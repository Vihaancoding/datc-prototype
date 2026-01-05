import os
import smtplib
from email.message import EmailMessage


import os
import smtplib
from email.message import EmailMessage
def send_approval_email(
    to_email,
    company,
    drone_id,
    approved_by,
    approved_role,      # 👈 ADD
    approved_at,
    airspace_type,
    max_distance_km,
    max_altitude_m,
    thrust_margin,
    thrust_state,
    safe_time,
    endurance_state,
    payload_ratio,
    wind_risk,
    qr_content
):



    print("DEBUG: send_approval_email CALLED")

    if not to_email:
        print("WARNING: No email provided for approval")
        return

    msg = EmailMessage()
    msg["Subject"] = "Drone Registration Approved – Operational Authorization Issued"
    msg["From"] = "authority@datc.gov"
    msg["To"] = to_email

    msg.set_content(f"""
Dear {company},

Your drone registration application has been APPROVED by the DATC Authority.
Drone ID: {drone_id}

Following a technical evaluation of the submitted specifications and
safety performance metrics, the drone has been granted operational
authorization under the following conditions:

────────────────────────────────
OPERATIONAL AUTHORIZATION
────────────────────────────────
Airspace Type: {airspace_type}
Maximum Operational Distance: {max_distance_km} km
Maximum Approved Altitude: {max_altitude_m} m
Authorization Mode: Automatic (Capability-Based)

────────────────────────────────
SAFETY ASSESSMENT SUMMARY
────────────────────────────────
• Thrust Margin: {thrust_margin}
• Thrust Margin Safety: {thrust_state}
• Safe Flight Time: {safe_time} minutes
• Endurance Status: {endurance_state}
• Payload Utilization Ratio: {payload_ratio}
• Wind Risk Assessment: {wind_risk}

These operational limits are derived from the drone’s certified capability
envelope and must be strictly complied with during all operations.

The official QR authorization has been issued and is attached to this email.
The QR must be affixed to the drone and presented during inspections.

────────────────────────────────
AUTHORIZATION DETAILS
Approved By: {approved_by}
Role: {approved_role}
Approved At: {approved_at}


Regards,
DATC Authority
Unmanned Aircraft Regulatory Division
""")

    # 📎 Attach QR code
    qr_path = f"qr_codes/{qr_content}.png"
    if qr_content and os.path.exists(qr_path):
        with open(qr_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="image",
                subtype="png",
                filename=f"{qr_content}.png"
            )
    else:
        print("WARNING: QR image not found for attachment")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("datcdroneregistery@gmail.com", "yyiv tgth qljf mbwg")
        server.send_message(msg)

    print("Approved QR authorization has been issued")


import smtplib
from email.message import EmailMessage


def send_denial_email(
    email,
    company,
    dtype,
    model,
    manu,
    year,
    submitted_at,
    reason_text,
    denied_by,
    denied_role,
    denied_at
):
    msg = EmailMessage()
    msg["Subject"] = "Drone Registration Application – DENIED"
    msg["From"] = "datcdroneregistry@gmail.com"
    msg["To"] = email

    body = f"""
Your drone registration application has been DENIED.

Application details:
- Company: {company}
- Type: {dtype}
- Model: {model}
- Manufacturer: {manu}
- Year: {year}
- Submitted on: {submitted_at}

Reason(s) for denial:
{reason_text}

No operational license or QR authorization has been issued.
You may submit a fresh application after correcting the issues.

--------------------------------
Denied by:
{denied_by}
{denied_role}
Date & Time: {denied_at}
--------------------------------

Regards,
DATC Authority
"""

    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(
            "datcdroneregistry@gmail.com",
            "YOUR_APP_PASSWORD"
        )
        server.send_message(msg)

    print("Denial email sent successfully")
