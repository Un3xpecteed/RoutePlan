import json
import os
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2 import Error as Psycopg2Error
from psycopg2 import OperationalError as Psycopg2OperationalError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import (
    NoSuchTableError,
    SQLAlchemyError,
)
from sqlalchemy.orm import sessionmaker

env_path_option = os.path.join(os.path.dirname(__file__), "..", ".env")

if os.path.exists(env_path_option):
    load_dotenv(dotenv_path=env_path_option)


DATABASE_USER = os.getenv("DATABASE_USER", "db_user")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "123")
DATABASE_HOST = os.getenv("DATABASE_HOST", "db")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "routeplan")

_DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(_DATABASE_URL, pool_pre_ping=True)
        except Exception as e:
            print(f"Error creating SQLAlchemy engine for {_DATABASE_URL}: {e}")
            raise
    return _engine


def get_db_session_new():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_get_engine()
        )
    return _SessionLocal()


def get_port_by_id(port_id: int) -> Optional[Dict[str, Any]]:
    try:
        with get_db_session_new() as db:
            query = text(
                "SELECT id, name, latitude, longitude FROM ports_port WHERE id = :port_id"
            )
            result = db.execute(query, {"port_id": port_id}).fetchone()
            if result:
                return (
                    dict(result._mapping)
                    if hasattr(result, "_mapping")
                    else dict(result)
                )
    except (
        SQLAlchemyError,
        NoSuchTableError,
    ) as e:
        print(f"Database error in get_port_by_id for port_id {port_id}: {e}")
        if isinstance(e, NoSuchTableError):
            print(
                f"CRITICAL: Table 'ports_port' not found during get_port_by_id for port {port_id}. Check migrations."
            )
    except Exception as e:
        print(f"Unexpected error in get_port_by_id for port_id {port_id}: {e}")
    return None


def get_all_ports_for_algorithm() -> List[Dict[str, Any]]:
    ports_data = []
    try:
        with get_db_session_new() as db:
            query = text(
                "SELECT id, name, latitude, longitude FROM ports_port ORDER BY id"
            )
            results = db.execute(query).fetchall()
            for row in results:
                ports_data.append(
                    dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
                )
    except (SQLAlchemyError, NoSuchTableError) as e:
        print(f"Database error in get_all_ports_for_algorithm: {e}")
        if isinstance(e, NoSuchTableError):
            print(
                "CRITICAL: Table 'ports_port' not found during get_all_ports_for_algorithm. Check migrations."
            )
    except Exception as e:
        print(f"Unexpected error in get_all_ports_for_algorithm: {e}")
    return ports_data


def get_segments_for_port(port_id: int) -> List[Dict[str, Any]]:
    segments_data = []
    try:
        with get_db_session_new() as db:
            query = text("""
                SELECT
                    s.id AS segment_id,
                    s."PortOfDeparture_id",
                    s."PortOfArrival_id",
                    s.distance,
                    p_arrival.id AS arrival_port_id,
                    p_arrival.name AS arrival_port_name,
                    p_arrival.latitude AS arrival_port_latitude,
                    p_arrival.longitude AS arrival_port_longitude
                FROM ports_segment s
                JOIN ports_port p_arrival ON s."PortOfArrival_id" = p_arrival.id
                WHERE s."PortOfDeparture_id" = :port_id
            """)
            results = db.execute(query, {"port_id": port_id}).fetchall()
            for row_proxy in results:
                row_dict = (
                    dict(row_proxy._mapping)
                    if hasattr(row_proxy, "_mapping")
                    else dict(row_proxy)
                )
                segments_data.append(
                    {
                        "id": row_dict["segment_id"],
                        "PortOfDeparture_id": row_dict["PortOfDeparture_id"],
                        "PortOfArrival_id": row_dict["arrival_port_id"],
                        "distance": row_dict["distance"],
                        "PortOfArrival": {
                            "id": row_dict["arrival_port_id"],
                            "name": row_dict["arrival_port_name"],
                            "latitude": row_dict["arrival_port_latitude"],
                            "longitude": row_dict["arrival_port_longitude"],
                        },
                    }
                )
    except (SQLAlchemyError, NoSuchTableError) as e:
        print(f"Database error in get_segments_for_port for port_id {port_id}: {e}")
        if isinstance(e, NoSuchTableError):
            print(
                f"CRITICAL: Table 'ports_segment' not found during get_segments_for_port for port {port_id}. Check migrations."
            )
    except Exception as e:
        print(f"Unexpected error in get_segments_for_port for port_id {port_id}: {e}")
    return segments_data


def check_db_connection():
    global _engine, _SessionLocal

    if _engine is not None:
        try:
            _engine.dispose()
            print(
                "Disposed of existing SQLAlchemy engine and connections for schema refresh."
            )
        except Exception as e:
            print(f"Error disposing SQLAlchemy engine: {e}")
        _engine = None
        _SessionLocal = None

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            options="-c default_transaction_read_only=off",
        )
        conn.autocommit = True

        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'ports_port'
            );
        """)
        table_exists = cursor.fetchone()[0]

        if table_exists:
            print("Table 'ports_port' found via direct psycopg2 check.")
            with get_db_session_new() as db:
                db.execute(text("SELECT 1 FROM ports_port LIMIT 1"))
            return True
        else:
            print("Table 'ports_port' NOT found via direct psycopg2 check.")
            return False

    except Psycopg2OperationalError as e:
        print(f"Direct psycopg2 connection failed: {e}")
        return False
    except Psycopg2Error as e:
        print(f"Direct psycopg2 query failed: {e}")
        return False
    except (SQLAlchemyError, NoSuchTableError) as e:
        print(f"SQLAlchemy query after psycopg2 check failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in check_db_connection: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_calculation_task(
    task_id: str,
    status: str,
    result_path: Optional[List[int]] = None,
    result_distance: Optional[float] = None,
    result_waypoints_data: Optional[List[Dict[str, Any]]] = None,
    vessel_speed_knots: Optional[float] = None,
    error_message: Optional[str] = None,
) -> bool:
    try:
        with get_db_session_new() as db:
            query = text("""
                UPDATE tasks_calculationtask
                SET status = :status,
                    result_path = :result_path,
                    result_distance = :result_distance,
                    result_waypoints_data = :result_waypoints_data,
                    vessel_speed_knots = :vessel_speed_knots,
                    error_message = :error_message,
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = :task_id
            """)
            params = {
                "task_id": task_id,
                "status": status,
                "result_path": json.dumps(result_path)
                if result_path is not None
                else None,
                "result_distance": result_distance,
                "result_waypoints_data": json.dumps(result_waypoints_data)
                if result_waypoints_data is not None
                else None,
                "vessel_speed_knots": vessel_speed_knots,
                "error_message": error_message,
            }
            db.execute(query, params)
            db.commit()
            print(f"Task {task_id} updated in DB: status={status}")
            return True
    except (SQLAlchemyError, NoSuchTableError) as e:
        print(f"Database error updating task {task_id}: {e}")
        if isinstance(e, NoSuchTableError):
            print(
                f"CRITICAL: Table 'tasks_calculationtask' not found during update for task {task_id}. Check migrations."
            )
    except Exception as e:
        print(f"Unexpected error updating task {task_id}: {e}")
    return False


if __name__ == "__main__":
    print("Running db_interface.py as a standalone script for testing.")
    if not check_db_connection():
        print("Failed to connect to the database or table 'ports_port' not found.")
    else:
        print("Database connection successful and 'ports_port' table found.")

        print("\n--- Testing get_port_by_id(1) ---")
        port1 = get_port_by_id(1)
        if port1:
            print(port1)
        else:
            print("Port with ID 1 not found (or table empty/non-existent).")

        print("\n--- Testing get_all_ports_for_algorithm() (first 3) ---")
        all_ports = get_all_ports_for_algorithm()
        if all_ports:
            for port_data in all_ports[:3]:
                print(port_data)
        else:
            print("No ports found (or table empty/non-existent).")

        print("\n--- Testing get_segments_for_port(1) ---")
        if port1:
            segments_from_port1 = get_segments_for_port(1)
            if segments_from_port1:
                for segment_data in segments_from_port1:
                    print(segment_data)
            else:
                print(
                    f"No segments found departing from port ID 1 ({port1.get('name', 'Unknown')}) (or table empty/non-existent)."
                )
        else:
            print("Skipping get_segments_for_port(1) because port 1 was not found.")
