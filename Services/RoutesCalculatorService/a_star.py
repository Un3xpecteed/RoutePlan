import heapq
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

# Импортируем модели из data_models.py
from data_models import PortData, SegmentDataForAStar

# Радиус Земли в морских милях
EARTH_RADIUS_NAUTICAL_MILES = 3440.098


def haversine_heuristic(port1: PortData, port2: PortData) -> float:
    """Эвристика: расстояние по прямой."""
    lat1, lon1 = math.radians(port1.latitude), math.radians(port1.longitude)
    lat2, lon2 = math.radians(port2.latitude), math.radians(port2.longitude)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_NAUTICAL_MILES * c


def reconstruct_path_from_data(
    came_from: Dict[int, Optional[int]],  # Изменил тип значения на Optional[int]
    current_port_id: int,
    all_ports_data: Dict[int, PortData],
) -> List[PortData]:
    """Восстанавливает путь, используя предоставленные данные о портах."""
    path_data: List[PortData] = []
    temp_id: Optional[int] = current_port_id  # temp_id может стать None
    while temp_id is not None:
        port_obj = all_ports_data.get(temp_id)
        if port_obj:
            path_data.append(port_obj)
        else:
            raise ValueError(
                f"Port with ID {temp_id} not found in all_ports_data during path reconstruction."
            )
        temp_id = came_from.get(temp_id)
    path_data.reverse()
    return path_data


def a_star_search_algorithm(
    start_port: PortData,
    end_port: PortData,
    all_ports_map: Dict[int, PortData],
    get_neighbors_callable: Callable[[int], List[Dict[str, Any]]],
) -> Tuple[Optional[List[PortData]], Optional[float]]:
    """
    Реализация A* для данных.
    get_neighbors_callable: функция(port_id: int) -> List[Dict[str, Any]]
    Возвращает (список_объектов_PortData_пути, общая_дистанция) или (None, None).
    """
    open_set: list[Tuple[float, int, PortData]] = []
    heapq.heappush(
        open_set,
        (0 + haversine_heuristic(start_port, end_port), start_port.id, start_port),
    )

    came_from: Dict[int, Optional[int]] = {start_port.id: None}

    g_score: Dict[int, float] = {port_id: float("inf") for port_id in all_ports_map}
    g_score[start_port.id] = 0

    f_score: Dict[int, float] = {port_id: float("inf") for port_id in all_ports_map}
    f_score[start_port.id] = haversine_heuristic(start_port, end_port)

    open_set_ids = {start_port.id}

    while open_set:
        current_f, current_port_id, current_port_obj = heapq.heappop(open_set)

        if current_port_id not in open_set_ids:
            continue
        open_set_ids.remove(current_port_id)

        if current_port_id == end_port.id:
            path = reconstruct_path_from_data(came_from, current_port_id, all_ports_map)
            return path, g_score[current_port_id]

        neighbor_segments_dicts = get_neighbors_callable(current_port_id)

        for segment_dict in neighbor_segments_dicts:
            try:
                segment_data = SegmentDataForAStar(**segment_dict)
                neighbor_port_obj = segment_data.PortOfArrival
            except Exception as e:
                print(
                    f"Warning: Could not parse segment data: {segment_dict}, error: {e}"
                )  # Логирование
                continue

            neighbor_port_id = neighbor_port_obj.id

            # Проверяем, есть ли сосед вообще в нашем графе all_ports_map.
            # Это важно, если get_neighbors_callable может вернуть сегмент к порту,
            # которого нет в all_ports_map (например, из-за фильтрации портов при загрузке).
            if neighbor_port_id not in all_ports_map:
                # print(f"Warning: Neighbor port ID {neighbor_port_id} not in all_ports_map. Skipping segment.")
                continue

            tentative_g_score = (
                g_score.get(current_port_id, float("inf")) + segment_data.distance
            )

            if tentative_g_score < g_score.get(neighbor_port_id, float("inf")):
                came_from[neighbor_port_id] = current_port_id
                g_score[neighbor_port_id] = tentative_g_score
                f_score[neighbor_port_id] = tentative_g_score + haversine_heuristic(
                    neighbor_port_obj, end_port
                )

                # Добавляем в кучу, даже если уже там (с худшим f_score).
                # Проверка `if current_port_id not in open_set_ids:` при извлечении отсеет старые.
                heapq.heappush(
                    open_set,
                    (f_score[neighbor_port_id], neighbor_port_id, neighbor_port_obj),
                )
                open_set_ids.add(
                    neighbor_port_id
                )  # Добавляем/обновляем, что он в очереди

    return None, None
