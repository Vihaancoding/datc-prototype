from typing import NamedTuple, Tuple, Optional
from datetime import datetime

import math


class Waypoint(NamedTuple):
    """A single point in 3D space that the drone must reach."""
    latitude: float
    longitude: float
    altitude_meters: float
    time_seconds: float


class FlightPlan(NamedTuple):
    """Complete specification of a drone flight mission."""
    flight_id: str
    start_time: datetime
    end_time: datetime
    waypoints: Tuple[Waypoint, ...]
    drone_radius_meters: float


class ValidationConfig(NamedTuple):
    """
    Configuration parameters for flight plan validation.

    SAFETY: All limits are configurable to support different jurisdictions
    and drone types without code changes.
    """
    # Altitude limits (meters AGL)
    max_altitude_meters: float = 120.0  # Default: US FAA Part 107 limit

    # Physical constraints
    min_drone_radius_meters: float = 0.5
    max_drone_radius_meters: float = 5.0

    # Temporal constraints
    min_time_delta_seconds: float = 0.1  # Minimum time between waypoints
    max_flight_duration_seconds: float = 3600.0  # 1 hour default
    max_advance_booking_days: float = 30.0

    # Tolerance for clock skew when checking future start times
    start_time_tolerance_seconds: float = 5.0

    # ADVANCED: Physical performance limits (optional checks)
    max_velocity_mps: Optional[float] = None  # meters per second
    max_climb_rate_mps: Optional[float] = None  # meters per second
    max_descent_rate_mps: Optional[float] = None  # meters per second
    max_acceleration_mps2: Optional[float] = None  # meters per second squared
    max_mission_range_meters: Optional[float] = None  # total path length

def _horizontal_distance_meters(wp1: Waypoint, wp2: Waypoint) -> float:
    """
    Approximate horizontal distance between two waypoints in meters.
    SAFETY: Used only for validation, not navigation.
    """
    R = 6371000.0  # Earth radius in meters

    lat1 = math.radians(wp1.latitude)
    lat2 = math.radians(wp2.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(wp2.longitude - wp1.longitude)

    x = dlon * math.cos((lat1 + lat2) / 2.0)
    y = dlat

    return math.sqrt(x * x + y * y) * R

def _calculate_total_path_length(waypoints: Tuple[Waypoint, ...]) -> float:
    """
    Calculate total horizontal path length in meters.
    SAFETY: Validation-only utility, deterministic and side-effect free.
    """
    total = 0.0
    for i in range(len(waypoints) - 1):
        total += _horizontal_distance_meters(waypoints[i], waypoints[i + 1])
    return total



def validate_flight_plan(
        plan: FlightPlan,
        config: ValidationConfig = ValidationConfig(),
        current_time: Optional[datetime] = None
) -> None:
    """
    Validate a flight plan against all approved DATC 1.0 safety rules.

    SAFETY: Fail-fast validation - stops at first violation to provide
    clear error messages and prevent cascading validation errors.

    Args:
        plan: The flight plan to validate
        config: Validation configuration parameters
        current_time: Current time for temporal checks (defaults to datetime.utcnow())

    Raises:
        ValueError: If any validation rule is violated, with specific error message

    ASSUMPTION: If current_time is None, uses datetime.utcnow() for temporal checks.
    This allows deterministic testing while supporting production use.
    """
    if current_time is None:
        current_time = datetime.utcnow()

    # =========================================================================
    # 1. STRUCTURAL INTEGRITY RULES
    # =========================================================================

    # Rule 1.2: Non-null Fields (check plan-level fields first)
    # SAFETY: Prevents null pointer errors in subsequent validation
    if plan.flight_id is None:
        raise ValueError("Rule 1.2 violation: flight_id cannot be None")
    if plan.start_time is None:
        raise ValueError("Rule 1.2 violation: start_time cannot be None")
    if plan.end_time is None:
        raise ValueError("Rule 1.2 violation: end_time cannot be None")
    if plan.waypoints is None:
        raise ValueError("Rule 1.2 violation: waypoints cannot be None")
    if plan.drone_radius_meters is None:
        raise ValueError("Rule 1.2 violation: drone_radius_meters cannot be None")

    # Rule 1.1: Waypoint Count
    # SAFETY: Minimum 2 waypoints required for a valid flight path
    if len(plan.waypoints) < 2:
        raise ValueError(
            f"Rule 1.1 violation: Flight plan must contain at least 2 waypoints, "
            f"got {len(plan.waypoints)}"
        )

    # Rule 1.2: Non-null Fields (check all waypoint fields)
    # SAFETY: Validates each waypoint before using in calculations
    for i, wp in enumerate(plan.waypoints):
        if wp.latitude is None:
            raise ValueError(f"Rule 1.2 violation: waypoint[{i}].latitude cannot be None")
        if wp.longitude is None:
            raise ValueError(f"Rule 1.2 violation: waypoint[{i}].longitude cannot be None")
        if wp.altitude_meters is None:
            raise ValueError(f"Rule 1.2 violation: waypoint[{i}].altitude_meters cannot be None")
        if wp.time_seconds is None:
            raise ValueError(f"Rule 1.2 violation: waypoint[{i}].time_seconds cannot be None")

    # =========================================================================
    # 7. IDENTIFIER RULES
    # =========================================================================

    # Rule 7.1: Non-empty Flight ID
    # SAFETY: Required for tracking and incident investigation
    if not plan.flight_id or len(plan.flight_id.strip()) == 0:
        raise ValueError("Rule 7.1 violation: flight_id must be non-empty")

    # NOTE: Rule 7.2 (Flight ID Uniqueness) requires external state (database)
    # and is explicitly excluded per task constraints

    # =========================================================================
    # 2. GEOGRAPHIC COORDINATE RULES
    # =========================================================================

    for i, wp in enumerate(plan.waypoints):
        # Rule 2.1: Latitude Bounds
        # SAFETY: Prevents physically impossible coordinates
        if wp.latitude < -90.0 or wp.latitude > 90.0:
            raise ValueError(
                f"Rule 2.1 violation: waypoint[{i}].latitude must be in range "
                f"[-90.0, 90.0], got {wp.latitude}"
            )

        # Rule 2.2: Longitude Bounds
        # SAFETY: Prevents invalid coordinates and routing errors
        if wp.longitude < -180.0 or wp.longitude > 180.0:
            raise ValueError(
                f"Rule 2.2 violation: waypoint[{i}].longitude must be in range "
                f"[-180.0, 180.0], got {wp.longitude}"
            )

        # NOTE: Rule 2.3 (Coordinate Precision) is treated as warning/normalization
        # per clarifications, not a hard validation failure

    # =========================================================================
    # 3. ALTITUDE RULES
    # =========================================================================

    for i, wp in enumerate(plan.waypoints):
        # Rule 3.1: Non-negative Altitude
        # SAFETY: Negative altitude implies terrain collision
        if wp.altitude_meters < 0.0:
            raise ValueError(
                f"Rule 3.1 violation: waypoint[{i}].altitude_meters must be >= 0.0, "
                f"got {wp.altitude_meters}"
            )

        # Rule 3.2: Maximum Altitude
        # SAFETY: Prevents airspace violations and manned aircraft conflicts
        if wp.altitude_meters > config.max_altitude_meters:
            raise ValueError(
                f"Rule 3.2 violation: waypoint[{i}].altitude_meters must be <= "
                f"{config.max_altitude_meters}, got {wp.altitude_meters}"
            )

    # =========================================================================
    # 6. PHYSICAL DIMENSION RULES
    # =========================================================================

    # Rule 6.1: Positive Drone Radius
    # SAFETY: Zero radius invalidates collision detection
    if plan.drone_radius_meters <= 0.0:
        raise ValueError(
            f"Rule 6.1 violation: drone_radius_meters must be > 0.0, "
            f"got {plan.drone_radius_meters}"
        )

    # Rule 6.3: Minimum Drone Radius
    # SAFETY: Accounts for GPS error and control uncertainty
    if plan.drone_radius_meters < config.min_drone_radius_meters:
        raise ValueError(
            f"Rule 6.3 violation: drone_radius_meters must be >= "
            f"{config.min_drone_radius_meters}, got {plan.drone_radius_meters}"
        )

    # Rule 6.2: Reasonable Drone Radius
    # SAFETY: Prevents excessively large radii that break deconfliction
    if plan.drone_radius_meters > config.max_drone_radius_meters:
        raise ValueError(
            f"Rule 6.2 violation: drone_radius_meters must be <= "
            f"{config.max_drone_radius_meters}, got {plan.drone_radius_meters}"
        )

    # =========================================================================
    # 4. TEMPORAL RULES
    # =========================================================================

    # Rule 4.4: First Waypoint at Time Zero
    # SAFETY: Establishes clear temporal reference point
    if plan.waypoints[0].time_seconds != 0.0:
        raise ValueError(
            f"Rule 4.4 violation: first waypoint time_seconds must be 0.0, "
            f"got {plan.waypoints[0].time_seconds}"
        )

    # Rule 4.1: Time Ordering
    # SAFETY: Prevents time paradoxes and infinite velocity
    for i in range(len(plan.waypoints) - 1):
        if plan.waypoints[i].time_seconds >= plan.waypoints[i + 1].time_seconds:
            raise ValueError(
                f"Rule 4.1 violation: waypoint times must be strictly increasing, "
                f"waypoint[{i}].time_seconds ({plan.waypoints[i].time_seconds}) >= "
                f"waypoint[{i + 1}].time_seconds ({plan.waypoints[i + 1].time_seconds})"
            )

    # Rule 4.5: Minimum Time Delta
    # SAFETY: Prevents infinite velocity and numeric instability
    for i in range(len(plan.waypoints) - 1):
        time_delta = plan.waypoints[i + 1].time_seconds - plan.waypoints[i].time_seconds
        if time_delta < config.min_time_delta_seconds:
            raise ValueError(
                f"Rule 4.5 violation: time delta between waypoints must be >= "
                f"{config.min_time_delta_seconds} seconds, got {time_delta} seconds "
                f"between waypoint[{i}] and waypoint[{i + 1}]"
            )

    # Rule 4.2: Start Time Before End Time
    # SAFETY: Flight cannot end before it begins
    if plan.start_time >= plan.end_time:
        raise ValueError(
            f"Rule 4.2 violation: start_time must be < end_time, "
            f"got start_time={plan.start_time}, end_time={plan.end_time}"
        )

    # Rule 4.3: Waypoint Times Within Authorization Window
    # SAFETY: Prevents flight outside authorized time window
    authorization_duration_seconds = (plan.end_time - plan.start_time).total_seconds()
    final_waypoint_time = plan.waypoints[-1].time_seconds
    EPSILON = 1e-6  # 1 microsecond tolerance

    if final_waypoint_time > authorization_duration_seconds + EPSILON:
        raise ValueError(
            f"Rule 4.3 violation: final waypoint time ({final_waypoint_time}s) "
            f"exceeds authorization window duration ({authorization_duration_seconds}s)"
        )


    # Rule 9.1: Future Start Time
    # SAFETY: Prevents authorization of flights in the past
    time_until_start = (plan.start_time - current_time).total_seconds()
    if time_until_start < -config.start_time_tolerance_seconds:
        raise ValueError(
            f"Rule 9.1 violation: start_time must be >= current_time "
            f"(with {config.start_time_tolerance_seconds}s tolerance), "
            f"start_time is {-time_until_start:.1f}s in the past"
        )

    # Rule 9.2: Reasonable Planning Horizon
    # SAFETY: Limits exposure to long-term uncertainty
    max_advance_seconds = config.max_advance_booking_days * 86400  # days to seconds
    if time_until_start > max_advance_seconds:
        raise ValueError(
            f"Rule 9.2 violation: start_time must be <= current_time + "
            f"{config.max_advance_booking_days} days, "
            f"start_time is {time_until_start / 86400:.1f} days in the future"
        )

    # Rule 9.3: Maximum Flight Duration
    # SAFETY: Prevents battery and endurance violations
    flight_duration_seconds = (plan.end_time - plan.start_time).total_seconds()
    if flight_duration_seconds > config.max_flight_duration_seconds:
        raise ValueError(
            f"Rule 9.3 violation: flight duration must be <= "
            f"{config.max_flight_duration_seconds}s, got {flight_duration_seconds}s"
        )

    # Rule 10.1: Authorization Window Contains Flight Duration
    # SAFETY: Ensures flight completes within authorization
    # NOTE: This is redundant with Rule 4.3 but kept for explicit clarity
    EPSILON = 1e-6  # 1 microsecond tolerance

    if authorization_duration_seconds + EPSILON < final_waypoint_time:
        raise ValueError(
            f"Rule 10.1 violation: authorization window ({authorization_duration_seconds}s) "
            f"must be >= final waypoint time ({final_waypoint_time}s)"
        )

    # =========================================================================
    # 8. PATH GEOMETRY RULES
    # =========================================================================

    # Rule 8.1: No Duplicate Consecutive Waypoints
    # SAFETY: Zero-length segments have undefined direction
    for i in range(len(plan.waypoints) - 1):
        wp1 = plan.waypoints[i]
        wp2 = plan.waypoints[i + 1]
        if (wp1.latitude == wp2.latitude and
                wp1.longitude == wp2.longitude and
                wp1.altitude_meters == wp2.altitude_meters):
            raise ValueError(
                f"Rule 8.1 violation: consecutive waypoints cannot have identical "
                f"coordinates, waypoint[{i}] and waypoint[{i + 1}] are duplicates"
            )

    # Rule 8.2: Total Path Length
    # SAFETY: Prevents zero-flight or impossible missions
    total_path_length = _calculate_total_path_length(plan.waypoints)

    if total_path_length <= 0.0:
        raise ValueError(
            f"Rule 8.2 violation: total path length must be > 0, "
            f"got {total_path_length}"
        )
    if config.max_mission_range_meters is not None:
        if total_path_length > config.max_mission_range_meters:
            raise ValueError(
                f"Rule 8.2 (ADVANCED) violation: total path length "
                f"{total_path_length:.1f} m exceeds max "
                f"{config.max_mission_range_meters} m"
            )

    # =========================================================================
    # ADVANCED CHECKS (OPTIONAL - Physical Performance)
    # =========================================================================
    # These checks are separated per clarifications and only run if
    # corresponding config parameters are provided
    # Rule 5.1 (ADVANCED): Maximum Velocity
    # SAFETY: Prevents physically impossible horizontal motion
    if config.max_velocity_mps is not None:
        for i in range(len(plan.waypoints) - 1):
            wp1 = plan.waypoints[i]
            wp2 = plan.waypoints[i + 1]

            distance = _horizontal_distance_meters(wp1, wp2)
            time_delta = wp2.time_seconds - wp1.time_seconds
            velocity = distance / time_delta

            if velocity > config.max_velocity_mps:
                raise ValueError(
                    f"Rule 5.1 (ADVANCED) violation: velocity between waypoint[{i}] "
                    f"and waypoint[{i + 1}] is {velocity:.2f} m/s, "
                    f"exceeds max {config.max_velocity_mps} m/s"
                )


    # Rule 3.3 (ADVANCED): Altitude Continuity
    # SAFETY: Prevents physically impossible vertical maneuvers
    if config.max_climb_rate_mps is not None or config.max_descent_rate_mps is not None:
        for i in range(len(plan.waypoints) - 1):
            wp1 = plan.waypoints[i]
            wp2 = plan.waypoints[i + 1]
            altitude_change = wp2.altitude_meters - wp1.altitude_meters
            time_delta = wp2.time_seconds - wp1.time_seconds
            vertical_rate = altitude_change / time_delta

            if altitude_change > 0 and config.max_climb_rate_mps is not None:
                if vertical_rate > config.max_climb_rate_mps:
                    raise ValueError(
                        f"Rule 3.3 (ADVANCED) violation: climb rate between "
                        f"waypoint[{i}] and waypoint[{i + 1}] is {vertical_rate:.2f} m/s, "
                        f"exceeds max climb rate {config.max_climb_rate_mps} m/s"
                    )

