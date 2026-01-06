from typing import NamedTuple, Optional
from enum import Enum

from flight_request import FlightRequest
from flight_planner import FlightPlan, generate_flight_plan
from flight_validation import validate_flight_plan


class ApprovalStatus(Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalResult(NamedTuple):
    """
    Result of processing a flight request.
    """
    status: ApprovalStatus
    flight_plan: Optional[FlightPlan]
    reason: Optional[str]


def handle_flight_request(request: FlightRequest) -> ApprovalResult:
    """
    Process a flight request through the approval pipeline.

    Returns APPROVED with FlightPlan if validation passes.
    Returns REJECTED with reason if validation fails.
    """
    try:
        plan = generate_flight_plan(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            end_lat=request.end_lat,
            end_lon=request.end_lon,
            start_time=request.requested_start_time,
            speed_mps=request.preferred_speed_mps,
        )

        validate_flight_plan(plan)

        return ApprovalResult(
            status=ApprovalStatus.APPROVED,
            flight_plan=plan,
            reason=None,
        )

    except ValueError as e:
        return ApprovalResult(
            status=ApprovalStatus.REJECTED,
            flight_plan=None,
            reason=str(e),
        )