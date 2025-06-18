from pydantic import BaseModel, Field


class PortData(BaseModel):
    id: int
    name: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class SegmentDataForAStar(BaseModel):
    id: int
    PortOfDeparture_id: int
    PortOfArrival_id: int
    distance: float
    PortOfArrival: PortData

    class Config:
        pass
