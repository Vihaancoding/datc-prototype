def compute_capability(
    motor_thrust,
    motor_count,
    takeoff_weight,
    max_payload,
    battery_wh,
    cruise_power,
    wind_limit
):
    motor_thrust = motor_thrust or 1.0
    motor_count = motor_count or 4
    takeoff_weight = takeoff_weight or 2.5
    max_payload = max_payload or 0.3
    battery_wh = battery_wh or 50.0
    cruise_power = cruise_power or 200.0
    wind_limit = wind_limit or 10

    thrust_margin = (motor_thrust * motor_count) / takeoff_weight
    if thrust_margin < 1.8:
        thrust_state = "UNSAFE"
    elif thrust_margin <= 2.2:
        thrust_state = "MARGINAL"
    else:
        thrust_state = "SAFE"

    max_time_min = (battery_wh / cruise_power) * 60
    safe_time = max_time_min * 0.75
    if safe_time < 10:
        endurance_state = "FAIL"
    elif safe_time <= 15:
        endurance_state = "LIMITED"
    else:
        endurance_state = "PASS"

    payload_ratio = max_payload / takeoff_weight

    if wind_limit < 15:
        wind_risk = "HIGH"
    elif wind_limit < 25:
        wind_risk = "MEDIUM"
    else:
        wind_risk = "LOW"

    return (
        thrust_margin,
        thrust_state,
        safe_time,
        endurance_state,
        payload_ratio,
        wind_risk
    )
