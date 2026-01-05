def auto_assign_authorization(
    thrust_margin,
    thrust_state,
    safe_time,
    endurance_state,
    payload_ratio,
    wind_risk
):
    if thrust_state != "SAFE" or endurance_state != "PASS":
        return "RESTRICTED", 1.0, 60

    if wind_risk == "HIGH":
        airspace = "RESTRICTED"
    elif wind_risk == "MEDIUM":
        airspace = "CONTROLLED"
    else:
        airspace = "OPEN"

    if safe_time < 10:
        max_dist = 1.0
    elif safe_time < 20:
        max_dist = 3.0
    elif safe_time < 40:
        max_dist = 8.0
    else:
        max_dist = 15.0

    if payload_ratio > 0.85:
        max_dist *= 0.5

    if thrust_margin > 1.8:
        max_dist *= 1.2

    max_alt = {
        "RESTRICTED": 60,
        "CONTROLLED": 90,
        "OPEN": 120
    }[airspace]

    return airspace, round(max_dist, 1), max_alt
