from typing import NamedTuple, Optional
from datetime import datetime
from enum import Enum
import math

from flight_planner import FlightPlan, Waypoint


# ============================================================================
# TELEMETRY DATA MODEL
# ============================================================================

class TelemetryUpdate(NamedTuple):
    """
    Real-time position report from a drone.
    Sent periodically during flight execution.
    """
    flight_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    altitude_meters: float


# ============================================================================
# FLIGHT HEALTH STATUS
# ============================================================================

class FlightHealthStatus(Enum):
    """
    Classification of drone flight health based on telemetry vs. approved plan.
    """
    ON_TRACK = "ON_TRACK"  # Within acceptable tolerances
    DELAYED = "DELAYED"  # Behind schedule but on correct path
    OFF_TRACK = "OFF_TRACK"  # Spatially deviated from planned route
    LOST = "LOST"  # No recent telemetry or catastrophic deviation


class FlightHealthReport(NamedTuple):
    """
    Result of analyzing telemetry against approved flight plan.
    """
    status: FlightHealthStatus
    reason: str
    position_error_meters: float
    altitude_error_meters: float
    time_error_seconds: float


# ============================================================================
# CONFIGURATION
# ============================================================================

# Spatial tolerance: how far drone can deviate from planned position
MAX_POSITION_ERROR_METERS = 10.0

# Altitude tolerance: how far drone can deviate from planned altitude
MAX_ALTITUDE_ERROR_METERS = 5.0

# Time tolerance: how late drone can be relative to plan
MAX_TIME_DELAY_SECONDS = 10.0

# Telemetry freshness: max age of telemetry before considering drone LOST
MAX_TELEMETRY_AGE_SECONDS = 30.0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points.
    """
    R = 6371000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def interpolate_expected_position(plan: FlightPlan, telemetry_time: datetime) -> Optional[tuple]:
    """
    Compute expected position at telemetry_time by interpolating between waypoints.

    Returns: (latitude, longitude, altitude_meters, expected_elapsed_seconds) or None if time is outside plan window
    """
    elapsed_seconds = (telemetry_time - plan.start_time).total_seconds()

    # Check if time is within flight plan window
    if elapsed_seconds < 0:
        return None  # Flight hasn't started yet

    total_duration = (plan.end_time - plan.start_time).total_seconds()
    if elapsed_seconds > total_duration:
        return None  # Flight should have ended

    # Find the two waypoints that bracket telemetry time
    waypoints = plan.waypoints

    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i + 1]

        if wp1.time_seconds <= elapsed_seconds <= wp2.time_seconds:
            # Interpolate between wp1 and wp2
            segment_duration = wp2.time_seconds - wp1.time_seconds

            if segment_duration > 0:
                t = (elapsed_seconds - wp1.time_seconds) / segment_duration
            else:
                t = 0.0

            expected_lat = wp1.latitude + t * (wp2.latitude - wp1.latitude)
            expected_lon = wp1.longitude + t * (wp2.longitude - wp1.longitude)
            expected_alt = wp1.altitude_meters + t * (wp2.altitude_meters - wp1.altitude_meters)

            return (expected_lat, expected_lon, expected_alt, elapsed_seconds)

    # If we reach here, use final waypoint (edge case for exact end time)
    final_wp = waypoints[-1]
    return (final_wp.latitude, final_wp.longitude, final_wp.altitude_meters, elapsed_seconds)


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def assess_flight_health(
        plan: FlightPlan,
        telemetry: TelemetryUpdate,
        current_time: datetime
) -> FlightHealthReport:
    """
    Assess drone flight health by comparing telemetry against approved plan.

    Classification logic (in priority order):
    1. LOST: Telemetry too old (stale data)
    2. LOST: Telemetry outside flight plan time window
    3. OFF_TRACK: Position or altitude deviation exceeds limits
    4. DELAYED: Drone is behind schedule but spatially correct
    5. ON_TRACK: All parameters within tolerances

    Args:
        plan: Approved FlightPlan (immutable)
        telemetry: Latest TelemetryUpdate from drone
        current_time: Current system time (for staleness check)

    Returns:
        FlightHealthReport with status and error metrics
    """

    # Step 1: Check telemetry freshness (LOST if too old)
    # This checks: current_time - telemetry.timestamp
    telemetry_age = (current_time - telemetry.timestamp).total_seconds()

    if telemetry_age > MAX_TELEMETRY_AGE_SECONDS:
        return FlightHealthReport(
            status=FlightHealthStatus.LOST,
            reason=f"Telemetry stale: {telemetry_age:.1f}s old (max {MAX_TELEMETRY_AGE_SECONDS}s)",
            position_error_meters=0.0,
            altitude_error_meters=0.0,
            time_error_seconds=telemetry_age,
        )

    if telemetry_age < 0:
        # Telemetry from the future (clock skew or invalid data)
        return FlightHealthReport(
            status=FlightHealthStatus.LOST,
            reason=f"Telemetry timestamp in future: {abs(telemetry_age):.1f}s ahead",
            position_error_meters=0.0,
            altitude_error_meters=0.0,
            time_error_seconds=abs(telemetry_age),
        )

    # Step 2: Check if telemetry is within flight plan time window
    elapsed_seconds = (telemetry.timestamp - plan.start_time).total_seconds()
    total_duration = (plan.end_time - plan.start_time).total_seconds()

    if elapsed_seconds < 0:
        return FlightHealthReport(
            status=FlightHealthStatus.LOST,
            reason=f"Telemetry before flight start: {abs(elapsed_seconds):.1f}s early",
            position_error_meters=0.0,
            altitude_error_meters=0.0,
            time_error_seconds=abs(elapsed_seconds),
        )

    if elapsed_seconds > total_duration + MAX_TELEMETRY_AGE_SECONDS:
        # Flight should have ended long ago
        return FlightHealthReport(
            status=FlightHealthStatus.LOST,
            reason=f"Telemetry after flight end: {elapsed_seconds - total_duration:.1f}s late",
            position_error_meters=0.0,
            altitude_error_meters=0.0,
            time_error_seconds=elapsed_seconds - total_duration,
        )

    # Step 3: Interpolate expected position from plan at telemetry timestamp
    expected_position = interpolate_expected_position(plan, telemetry.timestamp)

    if expected_position is None:
        return FlightHealthReport(
            status=FlightHealthStatus.LOST,
            reason="Cannot interpolate expected position from plan",
            position_error_meters=0.0,
            altitude_error_meters=0.0,
            time_error_seconds=0.0,
        )

    expected_lat, expected_lon, expected_alt, expected_elapsed = expected_position

    # Step 4: Calculate spatial errors
    position_error = haversine_distance_meters(
        telemetry.latitude,
        telemetry.longitude,
        expected_lat,
        expected_lon
    )

    altitude_error = abs(telemetry.altitude_meters - expected_alt)

    # Step 5: Calculate time error
    # Time error = how far behind the drone is relative to current_time
    # If current_time is ahead of where the drone should be, drone is delayed
    current_elapsed = (current_time - plan.start_time).total_seconds()
    time_error = current_elapsed - elapsed_seconds

    # Step 6: Classify health status (priority order matters)

    # Check for OFF_TRACK (spatial deviation takes priority over timing)
    if position_error > MAX_POSITION_ERROR_METERS:
        return FlightHealthReport(
            status=FlightHealthStatus.OFF_TRACK,
            reason=f"Position error {position_error:.1f}m exceeds limit {MAX_POSITION_ERROR_METERS}m",
            position_error_meters=position_error,
            altitude_error_meters=altitude_error,
            time_error_seconds=time_error,
        )

    if altitude_error > MAX_ALTITUDE_ERROR_METERS:
        return FlightHealthReport(
            status=FlightHealthStatus.OFF_TRACK,
            reason=f"Altitude error {altitude_error:.1f}m exceeds limit {MAX_ALTITUDE_ERROR_METERS}m",
            position_error_meters=position_error,
            altitude_error_meters=altitude_error,
            time_error_seconds=time_error,
        )

    # Check for DELAYED (behind schedule but spatially correct)
    if time_error > MAX_TIME_DELAY_SECONDS:
        return FlightHealthReport(
            status=FlightHealthStatus.DELAYED,
            reason=f"Time delay {time_error:.1f}s exceeds limit {MAX_TIME_DELAY_SECONDS}s",
            position_error_meters=position_error,
            altitude_error_meters=altitude_error,
            time_error_seconds=time_error,
        )

    # All checks passed: ON_TRACK
    return FlightHealthReport(
        status=FlightHealthStatus.ON_TRACK,
        reason="All parameters within acceptable tolerances",
        position_error_meters=position_error,
        altitude_error_meters=altitude_error,
        time_error_seconds=time_error,
    )