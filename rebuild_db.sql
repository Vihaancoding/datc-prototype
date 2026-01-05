-- =========================
-- CORE DRONES TABLE
-- =========================
CREATE TABLE IF NOT EXISTS drones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    name TEXT,
    Type TEXT,
    model TEXT,
    Manufacturer TEXT,
    year INTEGER,

    -- License & QR
    qr_content TEXT,
    qr_active INTEGER DEFAULT 0,
    state TEXT DEFAULT 'REGISTERED',
    license_expiry TEXT,

    -- Capability data
    motor_thrust REAL,
    motor_count INTEGER,
    takeoff_weight REAL,
    max_payload REAL,
    battery_wh REAL,
    cruise_power REAL,
    wind_limit REAL,

    thrust_margin REAL,
    safe_flight_time REAL,
    capability_status TEXT,

    -- Authorization
    airspace_type TEXT,
    max_distance_km REAL,
    max_altitude_m INTEGER,
    assignment_mode TEXT,

    -- Audit
    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    approved_by TEXT,
    approved_at TEXT
);

-- =========================
-- COMPANIES (OPTIONAL UI)
-- =========================
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    year_founded INTEGER,
    location TEXT
);

-- =========================
-- FLIGHT REQUESTS
-- =========================
CREATE TABLE IF NOT EXISTS flight_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drone_id INTEGER NOT NULL,
    origin TEXT,
    destination TEXT,
    path_json TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT DEFAULT 'PENDING',
    scheduled_time TEXT
);
