from flask import Flask, request, render_template
import sqlite3, os, uuid, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime
from cryptography.fernet import Fernet

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
fernet = Fernet(os.getenv("FERNET_KEY").encode())

app = Flask(__name__)

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import make_msgid
from pathlib import Path

def send_email(recipient_email, qr_path, is_active, verify_url):
    drone_id = os.path.splitext(os.path.basename(qr_path))[0]
    status = "✅ LICENSE VALID" if is_active else "❌ LICENSE SUSPENDED"

    msg = MIMEMultipart('related')
    msg['Subject'] = "DATC Drone Registration ✈️"
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = recipient_email

    # Generate CID for inline image
    image_cid = make_msgid(domain='datc-drones.org')

    # HTML content with correct verify_url
    html = f"""
    <html>
      <body>
        <h2>DATC Drone License</h2>
        <p>Thank you for registering your drone with DATC.</p>
        <p><strong>Drone ID:</strong> {drone_id}</p>
        <p><strong>Status:</strong> {status}</p>
        <p>Please wait while your license is being approved</p>
        <hr>
        <p style="font-size:small">If you did not register this drone, please contact DATCdroneregistery.com.</p>
      </body>
    </html>
    """

    # Attach HTML content
    msg.attach(MIMEText(html, 'html'))


    # Send email securely
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)



@app.route('/')
def form():
    return render_template('form.html')

from datetime import datetime, timedelta
@app.route('/submit', methods=['POST'])
def submit():

    name = request.form.get('name', '').strip()
    drone_type = request.form['type']
    year = request.form['year']
    model = request.form['model']
    manufacturer = request.form['manufacturer']
    email = request.form['email']
    controller = request.form.get('controller', '').strip()


    user_type = request.form['user_type']
    company_name = request.form.get('company_name', '').strip()

    # ✅ Create unique drone ID
    drone_id = f"DATC-{drone_type}-{year}-{company_name.replace(' ', '')}-{uuid.uuid4().hex[:6]}"

    qr_active ="0"


    # ✅ Set expiry 5 years from now
    issue_date = datetime.now()
    license_expiry = (issue_date + timedelta(days=5 * 365)).strftime('%Y-%m-%d')

    data = {
        "takeoff_weight": float(request.form["takeoff_weight"]),
        "max_payload": float(request.form["max_payload"]),
        "motor_thrust": float(request.form["motor_thrust"]),
        "motor_count": int(request.form["motor_count"]),
        "battery_wh": float(request.form["battery_wh"]),
        "cruise_power": float(request.form["cruise_power"]),
        "wind_limit": float(request.form["wind_limit"]),
    }

    # Validation
    if data["takeoff_weight"] <= 0:
        abort(400, "Invalid takeoff weight")

    if data["motor_count"] < 4:
        abort(400, "Motor count too low")

    if data["battery_wh"] <= 0:
        abort(400, "Invalid battery capacity")

    # Capability computation
    capability = compute_capability(data)

    if capability["status"] == "REJECT":
        abort(400, "Drone rejected: insufficient thrust margin")
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Submission timestamp (server-side)

    # ✅ Save drone data in database
    conn = sqlite3.connect('mydatabase.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO drones (
            name, Type, year, model, Manufacturer,
            email, qr_content, qr_active, qr_path,
            license_expiry, flight_controller,

            takeoff_weight, max_payload, motor_thrust, motor_count,
            battery_wh, cruise_power, wind_limit,
            thrust_margin, safe_flight_time, capability_status,
            submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        company_name, drone_type, year, model, manufacturer,
        email, drone_id, qr_active, qr_path,
        license_expiry, controller,

        data["takeoff_weight"],
        data["max_payload"],
        data["motor_thrust"],
        data["motor_count"],
        data["battery_wh"],
        data["cruise_power"],
        data["wind_limit"],
        capability["thrust_margin"],
        capability["safe_flight_time_min"],
        capability["status"],
        submitted_at
    ))

    conn.commit()
    conn.close()



    # ✅ Send confirmation email
    send_email(email, qr_path, False, verify_url)


    return render_template('success.html', drone_id=drone_id, status="Registered")



from flask import request, render_template
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os, sqlite3
from datetime import datetime

load_dotenv()
fernet = Fernet(os.getenv("FERNET_KEY").encode())
@app.route('/verify')
def verify():
    load_dotenv()

    token = request.args.get("token")
    if not token:
        return "<h1>❌ Invalid QR Code</h1><p>Missing token in the URL.</p>"

    try:
        drone_id = fernet.decrypt(token.encode()).decode()
    except:
        return render_template("tampered")
    # Now look up the drone by decrypted ID
    conn = sqlite3.connect('mydatabase.db')
    c = conn.cursor()
    c.execute("SELECT name, Type, year, model, Manufacturer, qr_active, license_expiry FROM drones WHERE qr_content = ?", (drone_id,))

    result = c.fetchone()
    conn.close()

    if not result:
        return render_template("not_found")

    name, dtype, year, model, manufacturer, active, license_expiry = result

    if datetime.strptime(license_expiry, "%Y-%m-%d") < datetime.now():
        status = "❌ LICENSE EXPIRED"
    else:
        status = "✅ LICENSE VALID" if active == 1 else "❌ LICENSE SUSPENDED"
    from flask import render_template

    return render_template("verify.html",
                           drone_id=drone_id,
                           name=name,
                           dtype=dtype,
                           year=year,
                           model=model,
                           manufacturer=manufacturer,
                           status=status,
                           license_expiry=license_expiry
                           )
''




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

