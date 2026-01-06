from datetime import datetime, timedelta
from flight_request import FlightRequest
from flight_unit import FlightPlanUnit
from flight_health import TelemetryUpdate

unit = FlightPlanUnit()

request = FlightRequest(
    company_id="ACME",
    drone_id="DRONE-01",
    start_lat=37.7749,
    start_lon=-122.4194,
    end_lat=37.7849,
    end_lon=-122.4094,
    requested_start_time=datetime.utcnow() + timedelta(seconds=10),
    preferred_speed_mps=10.0,
)

result = unit.handle_request(request)

if result.decision.name == "APPROVED":
    plan = result.flight_plan
    print("✓ Flight approved")

    telemetry = TelemetryUpdate(
        flight_id=plan.flight_id,
        timestamp=plan.start_time + timedelta(seconds=5),
        latitude=plan.waypoints[3].latitude,
        longitude=plan.waypoints[3].longitude,
        altitude_meters=plan.waypoints[3].altitude_meters,
    )

    health = unit.evaluate_health(plan, telemetry, datetime.utcnow())
    print("Health:", health)

else:
    print("✗ Rejected:", result.reason)
