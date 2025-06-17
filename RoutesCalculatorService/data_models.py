from pydantic import BaseModel, Field


class PortData(BaseModel):
    id: int
    name: str  # Имя порта, полезно для отладки и логов
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class SegmentDataForAStar(BaseModel):
    # Эта модель описывает данные о сегменте, как они приходят из db_interface.get_segments_for_port
    # и как они нужны для алгоритма A*
    id: int  # ID самого сегмента
    PortOfDeparture_id: int
    PortOfArrival_id: int  # ID порта прибытия, который есть в PortOfArrival
    distance: float
    PortOfArrival: PortData  # Вложенная Pydantic модель для данных порта прибытия

    class Config:
        pass


# Можно добавить другие модели данных, если они понадобятся, например:
# class CalculationResultMessage(BaseModel):
#     task_id: str
#     status: str
#     path: Optional[List[PortData]] = None
#     distance: Optional[float] = None
#     error_message: Optional[str] = None
