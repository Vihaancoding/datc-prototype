import sqlite3
import math
import json
from datetime import datetime, timedelta
from geopy.distance import geodesic

# ===== CONFIG =====
SPACING_METERS = 50
CRUISE_ALT = 30       # meters
SPEED_MPS = 10        # average horizontal speed
TAKEOFF_RATE = 3      # m/s vertical takeoff speed

# ===== 1. Create Database Table if Not Exists =====
def create_flight_table():
    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS flight_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drone_id TEXT,
            path_json TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

# ===== 2. Generate Waypoints with ETA =====
def generate_waypoints_with_eta(start_lat, start_lon, end_lat, end_lon, start_time, offset_deg=0):
    # Apply lateral offset
    start_lat += offset_deg
    start_lon += offset_deg
    end_lat += offset_deg
    end_lon += offset_deg

    start = (start_lat, start_lon)
    end = (end_lat, end_lon)
    total_distance = geodesic(start, end).meters
    num_segments = max(1, math.ceil(total_distance / SPACING_METERS))

    lat_step = (end_lat - start_lat) / num_segments
    lon_step = (end_lon - start_lon) / num_segments

    waypoints = []

    # Add takeoff segment
    takeoff_duration = CRUISE_ALT / TAKEOFF_RATE
    current_time = datetime.fromisoformat(start_time)
    waypoints.append({
        "lat": round(start_lat, 6),
        "lon": round(start_lon, 6),
        "alt": 0,
        "eta": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "takeoff"
    })

    current_time += timedelta(seconds=takeoff_duration)

    # Cruise segments
    for i in range(num_segments + 1):
        lat = start_lat + i * lat_step
        lon = start_lon + i * lon_step
        eta = current_time + timedelta(seconds=(i * SPACING_METERS / SPEED_MPS))
        waypoints.append({
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "alt": CRUISE_ALT,
            "eta": eta.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "cruise"
        })

    return waypoints

# ===== 3. Check if Path Conflicts with Any Existing Flights =====
def is_conflicting(new_path, new_start, new_end, existing_flights, threshold=40):
    new_start = datetime.fromisoformat(new_start)
    new_end = datetime.fromisoformat(new_end)

    for flight in existing_flights:
        existing_start = datetime.fromisoformat(flight['start_time'])
        existing_end = datetime.fromisoformat(flight['end_time'])

        if new_start < existing_end and new_end > existing_start:
            existing_path = json.loads(flight['path_json'])
            for wp1 in new_path:
                for wp2 in existing_path:
                    dist = geodesic((wp1['lat'], wp1['lon']), (wp2['lat'], wp2['lon'])).meters
                    if dist < threshold:
                        return True
    return False

# ===== 4. Generate a Safe Plan (tries offsets and time delays) =====
def generate_safe_plan(start_lat, start_lon, end_lat, end_lon, start_time, existing_flights):
    for offset_try in range(5):
        offset = offset_try * 0.0003
        path = generate_waypoints_with_eta(start_lat, start_lon, end_lat, end_lon, start_time, offset_deg=offset)
        end_time = path[-1]['eta']
        if not is_conflicting(path, start_time, end_time, existing_flights):
            return path, start_time, end_time

    for delay_try in range(1, 4):
        delayed_start = (datetime.fromisoformat(start_time) + timedelta(minutes=delay_try * 5)).isoformat()
        path = generate_waypoints_with_eta(start_lat, start_lon, end_lat, end_lon, delayed_start)
        end_time = path[-1]['eta']
        if not is_conflicting(path, delayed_start, end_time, existing_flights):
            return path, delayed_start, end_time

    return None, None, None

# ===== 5. Save Flight Plan to DB =====
def save_flight_plan(drone_id, path, start_time, end_time):
    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO flight_plans (drone_id, path_json, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        drone_id,
        json.dumps(path),
        start_time,
        end_time,
        "scheduled"
    ))
    conn.commit()
    conn.close()

# ===== ✅ RUN THIS EXAMPLE =====
if __name__ == "__main__":
    create_flight_table()

    # Step 1: Load existing flights
    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("SELECT drone_id, start_time, end_time, path_json FROM flight_plans WHERE status = 'scheduled'")
    existing_flights = [
        {"drone_id": row[0], "start_time": row[1], "end_time": row[2], "path_json": row[3]}
        for row in c.fetchall()
    ]
    conn.close()

    # Step 2: Request new flight plan
    drone_id = "DATC-DELIVERY-2025-XYZ123"
    start_lat, start_lon = 28.6135, 77.2095
    end_lat, end_lon = 28.6152, 77.2125
    requested_start = "2025-07-14T16:10:00"

    path, safe_start, safe_end = generate_safe_plan(start_lat, start_lon, end_lat, end_lon, requested_start, existing_flights)

    if path:
        save_flight_plan(drone_id, path, safe_start, safe_end)
        print(f"✅ Flight plan saved for {drone_id}")
        for wp in path:
            print(wp)
    else:
        print("❌ Could not generate a safe flight plan.")
