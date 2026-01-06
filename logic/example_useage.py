from datetime import datetime, timedelta
from flight_request import FlightRequest
from flight_approval import handle_flight_request, ApprovalStatus


request = FlightRequest(
    company_id="ACME-CORP",
    drone_id="DRONE-001",
    start_lat=37.7749,
    start_lon=-122.4194,
    end_lat=37.7849,
    end_lon=-122.4094,
    requested_start_time=datetime.utcnow() + timedelta(hours=1),
    preferred_speed_mps=10.0,
)

result = handle_flight_request(request)

if result.status == ApprovalStatus.APPROVED:
    print(f"✓ APPROVED: Flight {result.flight_plan.flight_id}")
    print(f"  Waypoints: {len(result.flight_plan.waypoints)}")
    print(f"  Duration: {(result.flight_plan.end_time - result.flight_plan.start_time).total_seconds()}s")
else:
    print(f"✗ REJECTED: {result.reason}")


bad_request = FlightRequest(
    company_id="ACME-CORP",
    drone_id="DRONE-002",
    start_lat=37.7749,
    start_lon=-122.4194,
    end_lat=37.7849,
    end_lon=-122.4094,
    requested_start_time=datetime.utcnow() - timedelta(hours=1),
    preferred_speed_mps=10.0,
)

result = handle_flight_request(bad_request)

if result.status == ApprovalStatus.APPROVED:
    print(f"✓ APPROVED: Flight {result.flight_plan.flight_id}")
else:
    print(f"✗ REJECTED: {result.reason}")