from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
import bcrypt
import random
import json
import networkx as nx
from shapely.geometry import Point

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_KEY"

@app.before_request
def allow_external_dev():
    if app.debug and request.endpoint == 'home':
        session.setdefault('company', 'DEV')


# ✅ Make `company` available to all templates automatically
@app.context_processor
def inject_company():
    return dict(company=session.get("company"))

# ✅ Home page (Sign-in with captcha)
@app.route('/')
def home():
    num1, num2 = random.randint(1, 9), random.randint(1, 9)
    session['captcha_answer'] = num1 + num2
    return render_template("website.html", error=None, num1=num1, num2=num2)

# ✅ Login with captcha validation
@app.route('/login', methods=['POST'])
def login():
    name = request.form['company_name']
    password = request.form['password']
    user_captcha = request.form['captcha']

    # ✅ Captcha safety check
    try:
        if int(user_captcha) != session.get('captcha_answer'):
            return refresh_login("❌ Incorrect captcha. Try again.")
    except ValueError:
        return refresh_login("❌ Please enter a valid number for captcha.")

    # ✅ Check credentials
    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("SELECT password FROM Companylog WHERE name = ?", (name,))
    row = c.fetchone()
    conn.close()

    if row and bcrypt.checkpw(password.encode(), row[0].encode() if isinstance(row[0], str) else row[0]):
        session['company'] = name
        return redirect(url_for('dashboard'))

    return refresh_login("❌ Invalid credentials.")

def refresh_login(error_msg):
    num1, num2 = random.randint(1, 9), random.randint(1, 9)
    session['captcha_answer'] = num1 + num2
    return render_template("website.html", error=error_msg, num1=num1, num2=num2)

# ✅ Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ✅ Dashboard
@app.route('/dashboard')
def dashboard():
    company = session.get("company")
    if not company:
        return redirect(url_for('home'))

    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("SELECT qr_content, Type, year, qr_active, id FROM drones WHERE name = ?", (company,))
    drones = c.fetchall()
    conn.close()

    cleaned_drones = []
    for d in drones:
        raw_id = d[0]
        if raw_id is None:
            clean_id = "Unknown"
        elif "id=" in raw_id:
            clean_id = raw_id.split("id=")[-1]
        elif "token=" in raw_id:
            clean_id = raw_id.split("token=")[-1]
        else:
            clean_id = raw_id
        cleaned_drones.append((clean_id, d[1], d[2], d[3], d[4]))

    return render_template("dashboard.html", drones=cleaned_drones)

# ✅ Drone map
@app.route('/drone_map/<drone_id>')
def drone_map(drone_id):
    lat, lng = round(random.uniform(19.0, 28.6), 6), round(random.uniform(72.8, 77.3), 6)
    return render_template("drone_map.html", drone_id=drone_id, lat=lat, lng=lng)

# ✅ Manage Flights (Session-based company check)
@app.route('/manage_flights')
def manage_flights():
    company = session.get("company")
    if not company:
        return redirect(url_for('home'))

    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("""
        SELECT fr.id, fr.drone_id, fr.origin, fr.destination, fr.date, 
               fr.flight_time, fr.status, fr.waypoints
        FROM flight_requests fr
        JOIN drones d ON fr.drone_id = d.qr_content
        WHERE d.name = ?
    """, (company,))
    flights = c.fetchall()
    conn.close()

    # ✅ Convert JSON waypoints to Python list for better readability in template
    formatted_flights = []
    for f in flights:
        waypoints = json.loads(f[7]) if f[7] else []
        formatted_flights.append((f[0], f[1], f[2], f[3], f[4], f[5], f[6], waypoints))

    return render_template("manage_flights.html", flights=formatted_flights)


@app.route('/update_flight_status/<int:flight_id>/<string:status>')
def update_flight_status(flight_id, status):
    conn = sqlite3.connect("mydatabase.db")
    c = conn.cursor()
    c.execute("UPDATE flight_requests SET status = ? WHERE id = ?", (status, flight_id))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_flights'))

# ✅ Common Flight Plan Generator (A* path planning)
def generate_flight_plan(origin, destination):
    o_lat, o_lng = map(float, origin.split(','))
    d_lat, d_lng = map(float, destination.split(','))

    restricted_zones = [
        {"lat": 23.5, "lng": 75.2, "radius": 5},
        {"lat": 25.1, "lng": 77.0, "radius": 3}
    ]

    G = nx.grid_2d_graph(100, 100)
    min_lat, max_lat = min(o_lat, d_lat) - 1, max(o_lat, d_lat) + 1
    min_lng, max_lng = min(o_lng, d_lng) - 1, max(o_lng, d_lng) + 1

    def grid_to_coords(i, j):
        lat = min_lat + (max_lat - min_lat) * (i / 99)
        lng = min_lng + (max_lng - min_lng) * (j / 99)
        return lat, lng

    for node in list(G.nodes):
        lat, lng = grid_to_coords(*node)
        for zone in restricted_zones:
            dist_km = Point(lat, lng).distance(Point(zone["lat"], zone["lng"])) * 111
            if dist_km < zone["radius"]:
                G.remove_node(node)

    def nearest_node(lat, lng):
        i = int((lat - min_lat) / (max_lat - min_lat) * 99)
        j = int((lng - min_lng) / (max_lng - min_lng) * 99)
        return (max(0, min(99, i)), max(0, min(99, j)))

    start = nearest_node(o_lat, o_lng)
    end = nearest_node(d_lat, d_lng)

    try:
        path_nodes = nx.astar_path(G, start, end)
        waypoints = [grid_to_coords(i, j) for i, j in path_nodes]
        waypoints[0] = (o_lat, o_lng)
        waypoints[-1] = (d_lat, d_lng)
    except nx.NetworkXNoPath:
        waypoints = [(o_lat, o_lng), (d_lat, d_lng)]

    return waypoints

# ✅ Flight Plan Map
@app.route('/flight_plan_map')
def flight_plan_map():
    drone_id = request.args.get('drone_id')
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    flight_time = request.args.get('time')

    waypoints = generate_flight_plan(origin, destination)
    o_lat, o_lng = map(float, origin.split(','))
    d_lat, d_lng = map(float, destination.split(','))

    restricted_zones = [
        {"lat": 23.5, "lng": 75.2, "radius": 5},
        {"lat": 25.1, "lng": 77.0, "radius": 3}
    ]

    return render_template(
        "flight_plan_map.html",
        drone_id=drone_id,
        o_lat=o_lat, o_lng=o_lng,
        d_lat=d_lat, d_lng=d_lng,
        flight_time=flight_time,
        restricted_zones=restricted_zones,
        waypoints=waypoints
    )

# ✅ Request Flight Plan
@app.route('/request_flight_plan/<drone_id>', methods=['GET', 'POST'])
def request_flight_plan(drone_id):
    if request.method == 'POST':
        origin = request.form['origin']
        destination = request.form['destination']
        date = request.form['date']
        time = request.form['time']

        waypoints = generate_flight_plan(origin, destination)

        conn = sqlite3.connect("mydatabase.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO flight_requests (drone_id, origin, destination, date, flight_time, waypoints)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (drone_id, origin, destination, date, time, json.dumps(waypoints)))
        conn.commit()
        conn.close()

        return redirect(url_for('flight_plan_map',
                                drone_id=drone_id,
                                origin=origin,
                                destination=destination,
                                time=time))

    lat = round(random.uniform(19.0, 28.6), 6)
    lng = round(random.uniform(72.8, 77.3), 6)
    origin = f"{lat},{lng}"

    return render_template('request_flight_plan.html',
                           drone_id=drone_id, origin=origin,
                           company=session.get("company"))

if __name__ == '__main__':
    app.run(debug=True)