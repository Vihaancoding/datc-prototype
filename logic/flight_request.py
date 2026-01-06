from typing import NamedTuple
from datetime import datetime


class FlightRequest(NamedTuple):
    """
    Represents a company's request to fly a drone.
    This is what gets submitted to the approval pipeline.
    """
    company_id: str
    drone_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    requested_start_time: datetime
    preferred_speed_mps: float