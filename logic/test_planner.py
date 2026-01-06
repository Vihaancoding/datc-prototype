from datetime import datetime, timedelta

from flight_planner import generate_flight_plan

from flight_validation import validate_flight_plan, ValidationConfig

print("Running flight planner test...")

start_time = datetime.utcnow() + timedelta(seconds=10)

plan = generate_flight_plan( start_lat=0.0,
    start_lon=0.0,
    end_lat=0.0,
    end_lon=0.001,
    start_time=start_time,
    speed_mps=10.0,
    # arguments your planner expects
)

validate_flight_plan(plan, ValidationConfig(max_velocity_mps=12.0))

print("✅ Flight planner test PASSED")
