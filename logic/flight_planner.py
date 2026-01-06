from typing import NamedTuple, List, Tuple
from datetime import datetime


# SAFETY: Using NamedTuple for immutability - flight plans cannot be
# accidentally modified after validation

class Waypoint(NamedTuple):
    """
    A single point in 3D space that the drone must reach.

    SAFETY RATIONALE:
    - latitude/longitude: WGS84 coordinates for global positioning
    - altitude_meters: Height above ground level (AGL) for collision avoidance
    - time_seconds: Time from flight start when drone reaches this point
      (enables time-based conflict detection between multiple drones)
    """
    latitude: float  # Decimal degrees, range: -90.0 to 90.0
    longitude: float  # Decimal degrees, range: -180.0 to 180.0
    altitude_meters: float  # Meters AGL, must be >= 0
    time_seconds: float  # Seconds from flight start, must be >= 0


class FlightPlan(NamedTuple):
    """
    Complete specification of a drone flight mission.

    SAFETY RATIONALE:
    - Immutable structure prevents mid-flight modifications
    - All fields required for collision detection and authorization
    - Minimal design reduces validation complexity
    """

    # IDENTIFICATION
    flight_id: str  # Unique identifier for this flight plan

    # TIME-BASED AUTHORIZATION
    start_time: datetime  # UTC timestamp when flight is authorized to begin
    end_time: datetime  # UTC timestamp when flight must be completed

    # SPATIAL PATH (COLLISION DETECTION)
    waypoints: Tuple[Waypoint, ...]  # Ordered sequence of waypoints
    # Tuple (not List) for immutability
    # Must contain at least 2 waypoints

    # PHYSICAL CONSTRAINTS (COLLISION DETECTION)
    drone_radius_meters: float  # Safety buffer around drone's physical size
    # Used for collision cylinder calculation

# ASSUMPTIONS MADE:
# 1. Altitude is AGL (Above Ground Level), not MSL (Mean Sea Level)
#    - Simpler for obstacle avoidance near ground
#    - If MSL needed, conversion layer can be added separately
#
# 2. Straight-line interpolation between waypoints
#    - Drone travels in straight lines between consecutive waypoints
#    - Actual path is deterministic and calculable
#
# 3. Constant velocity between waypoints
#    - Speed = distance / (time_delta between waypoints)
#    - Enables precise position calculation at any time
#
# 4. Single drone per flight plan
#    - No formation flying in this minimal design
#
# 5. Time is monotonically increasing through waypoints
#    - waypoints[i].time_seconds < waypoints[i+1].time_seconds
#
# 6. Drone radius includes all safety margins
#    - Accounts for GPS uncertainty, control errors, physical size

import math
from datetime import datetime, timedelta

WAYPOINT_INTERVAL_SECONDS = 2.0
CRUISE_ALTITUDE_METERS = 30.0
GROUND_ALTITUDE_METERS = 0.0
MAX_CLIMB_RATE_MPS = 3.0
MAX_DESCENT_RATE_MPS = 3.0


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points on Earth using Haversine formula.
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


def compute_altitude_at_time(
        elapsed_time: float,
        climb_duration: float,
        cruise_duration: float,
        descent_duration: float,
        peak_altitude: float
) -> float:
    """
    Compute altitude based on elapsed time through flight phases.

    Phase structure:
    - [0, climb_duration]: climb from 0 to peak_altitude
    - [climb_duration, climb_duration + cruise_duration]: cruise at peak_altitude
    - [climb_duration + cruise_duration, total_duration]: descend to 0

    Returns altitude in meters.
    """
    if elapsed_time <= climb_duration:
        # Climb phase: linear altitude gain
        if climb_duration > 0:
            return (elapsed_time / climb_duration) * peak_altitude
        else:
            return peak_altitude

    elif elapsed_time <= climb_duration + cruise_duration:
        # Cruise phase: constant altitude
        return peak_altitude

    else:
        # Descent phase: linear altitude loss
        time_into_descent = elapsed_time - climb_duration - cruise_duration
        if descent_duration > 0:
            return peak_altitude - (time_into_descent / descent_duration) * peak_altitude
        else:
            return GROUND_ALTITUDE_METERS


def generate_flight_plan(
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        start_time: datetime,
        speed_mps: float = 10.0,
) -> FlightPlan:
    """
    Straight-line flight planner with time-based altitude profile (DATC Phase C).

    Strategy:
    1. Calculate horizontal distance and minimum flight time (distance / speed)
    2. Calculate ideal climb/descent times based on max rates
    3. If total time allows, use full cruise altitude with climb → cruise → descent
    4. If flight is too short, reduce peak altitude proportionally
    5. Generate waypoints at regular time intervals
    6. Compute altitude for each waypoint based on elapsed time
    """

    # Step 1: Calculate horizontal distance and base flight time
    horizontal_distance = haversine_distance_meters(start_lat, start_lon, end_lat, end_lon)
    minimum_flight_time = horizontal_distance / speed_mps

    # Step 2: Calculate ideal climb and descent times for full cruise altitude
    ideal_climb_time = (CRUISE_ALTITUDE_METERS - GROUND_ALTITUDE_METERS) / MAX_CLIMB_RATE_MPS
    ideal_descent_time = (CRUISE_ALTITUDE_METERS - GROUND_ALTITUDE_METERS) / MAX_DESCENT_RATE_MPS

    # Step 3: Determine if flight is long enough for full altitude profile
    if minimum_flight_time >= ideal_climb_time + ideal_descent_time:
        # Normal flight: full climb, cruise, then descent
        climb_duration = ideal_climb_time
        descent_duration = ideal_descent_time
        cruise_duration = minimum_flight_time - climb_duration - descent_duration
        peak_altitude = CRUISE_ALTITUDE_METERS
    else:
        # Short flight: reduce peak altitude, no cruise phase
        # Split time equally between climb and descent
        climb_duration = minimum_flight_time / 2.0
        descent_duration = minimum_flight_time / 2.0
        cruise_duration = 0.0
        # Peak altitude limited by available time
        peak_altitude = climb_duration * MAX_CLIMB_RATE_MPS

    total_duration = climb_duration + cruise_duration + descent_duration

    # Step 4: Calculate number of waypoint segments
    num_segments = math.ceil(total_duration / WAYPOINT_INTERVAL_SECONDS)
    if num_segments < 1:
        num_segments = 1

    # Step 5: Generate waypoints with time-based altitude computation
    waypoints = []
    for i in range(num_segments + 1):
        t = i / num_segments  # Normalized time [0.0, 1.0]
        elapsed_time = t * total_duration

        # Compute altitude based on time through flight phases
        altitude = compute_altitude_at_time(
            elapsed_time,
            climb_duration,
            cruise_duration,
            descent_duration,
            peak_altitude
        )

        # Linear interpolation of lat/lon along great-circle path
        wp = Waypoint(
            latitude=start_lat + t * (end_lat - start_lat),
            longitude=start_lon + t * (end_lon - start_lon),
            altitude_meters=altitude,
            time_seconds=elapsed_time,
        )
        waypoints.append(wp)

    # Step 6: Compute end_time with small buffer to avoid floating-point validation failures
    # The validator checks that final waypoint time <= authorization window duration
    # Add 1 microsecond buffer to handle floating-point precision issues
    end_time = start_time + timedelta(seconds=total_duration, microseconds=1)

    return FlightPlan(
        flight_id="TEST-FLIGHT",
        start_time=start_time,
        end_time=end_time,
        waypoints=tuple(waypoints),
        drone_radius_meters=1.0,
    )

