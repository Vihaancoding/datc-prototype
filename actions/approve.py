from db.db_helpers import get_db
from logic.capability import compute_capability
from logic.authorization import auto_assign_authorization
from emailer.notifications import send_approval_email
from logic.auth_context import CURRENT_AUTHORIZER, current_timestamp
from datetime import datetime
import qrcode
from PIL import Image
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
fernet = Fernet(os.getenv("FERNET_KEY").encode())


def generate_qr_with_logo(data, logo_path, output_path):
    # Step 1: Create QR code
    qr = qrcode.QRCode(
        version=4,  # smaller QR version (1–40)
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High correction for logo overlay
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Step 2: Create QR image
    qr_img = qr.make_image(
        fill_color="#003366",  # dark blue
        back_color="white"
    ).convert("RGB")

    # Step 3: Load the owl logo
    logo = Image.open(logo_path)

    # Step 4: Resize logo relative to QR code
    qr_width, qr_height = qr_img.size
    logo_size = int(qr_width / 4)  # logo is 1/4th of QR size
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Step 5: Paste logo into center of QR
    pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
    qr_img.paste(logo, pos, mask=logo if logo.mode == 'RGBA' else None)

    # Step 6: Save final QR code
    qr_img.save(output_path)
    return output_path



def approve_drone(
    current_drone_id,
    pending_qr_map,
    auto_assign_var,
    airspace_var,
    max_distance_var,
    max_altitude_var,
    status_var,
    load_pending_list,
    show_empty_detail
):

    if CURRENT_AUTHORIZER.get("role") != "Senior Authorizer":
        messagebox.showerror(
            "Permission Denied",
            "You are not authorized to approve this drone."
        )
        return

    if not current_drone_id:
        return

    if getattr(approve_drone, "_locked", False):
        print("DEBUG: approve_drone blocked (already executed)")
        return


    approve_drone._locked = True

    if not current_drone_id:
        return

    conn = get_db()
    cur = conn.cursor()

    # 🔍 Fetch drone + email data
    cur.execute("""
        SELECT
            email,
            name,
            motor_thrust,
            motor_count,
            takeoff_weight,
            max_payload,
            battery_wh,
            cruise_power,
            wind_limit
        FROM drones
        WHERE id = ?
    """, (current_drone_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return

    (
        email,
        company,
        motor_thrust,
        motor_count,
        takeoff_weight,
        max_payload,
        battery_wh,
        cruise_power,
        wind_limit
    ) = row

    # 🧠 Capability computation
    (
        thrust_margin,
        thrust_state,
        safe_time,
        endurance_state,
        payload_ratio,
        wind_risk
    ) = compute_capability(
        motor_thrust,
        motor_count,
        takeoff_weight,
        max_payload,
        battery_wh,
        cruise_power,
        wind_limit
    )

    qr_content = pending_qr_map[current_drone_id]

    # 🧭 Authorization assignment
    if auto_assign_var.get():
        airspace, max_dist, max_alt = auto_assign_authorization(
            thrust_margin,
            thrust_state,
            safe_time,
            endurance_state,
            payload_ratio,
            wind_risk
        )
        assignment_mode = "AUTO"
    else:
        airspace = airspace_var.get()
        max_dist = float(max_distance_var.get())
        max_alt = int(max_altitude_var.get())
        assignment_mode = "MANUAL"

    # ✅ SINGLE-SOURCE VARIABLES
    approved_by = CURRENT_AUTHORIZER["name"]
    approved_role = CURRENT_AUTHORIZER["role"]
    approved_at = current_timestamp()

    # 💾 Update DB
    cur.execute("""
        UPDATE drones
        SET
            state = 'APPROVED',
            qr_active = 1,
            airspace_type = ?,
            max_distance_km = ?,
            max_altitude_m = ?,
            assignment_mode = ?,
            approved_by = ?,
            approved_at = ?
        WHERE id = ?
    """, (
        airspace,
        max_dist,
        max_alt,
        assignment_mode,
        approved_by,
        approved_at,
        current_drone_id
    ))

    conn.commit()
    conn.close()

    def generate_qr(drone_id):
        encrypted = fernet.encrypt(drone_id.encode()).decode()
        verify_url = f"{BASE_URL}/verify?token={encrypted}"

        logo_path = "owl_logo.png"  # ✅ No comma here
        output_path = f"qr_codes/{drone_id}.png"

        # Step 1: Generate QR with high error correction
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # allow space for logo
            box_size=10,
            border=4,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        # Step 2: Open and resize logo
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            qr_width, qr_height = qr_img.size
            logo_size = int(qr_width / 4)
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

            # Step 3: Paste logo in center
            pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
            qr_img.paste(logo, pos, mask=logo if logo.mode == 'RGBA' else None)

        else:
            print("⚠️ Warning: Logo not found, saving plain QR")

        # Step 4: Save final QR image
        qr_img.save(output_path)
        return verify_url, output_path

    # 📧 Send approval email (NEW SIGNATURE)
    approved_by = CURRENT_AUTHORIZER["name"]
    approved_role = CURRENT_AUTHORIZER["role"]
    approved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # ✅ Generate QR code with encrypted token
    verify_url, qr_path = generate_qr(qr_content)

    send_approval_email(
        email,
        company,
        current_drone_id,
        approved_by,
        approved_role,
        approved_at,
        airspace,
        max_dist,
        max_alt,
        thrust_margin,
        thrust_state,
        safe_time,
        endurance_state,
        payload_ratio,
        wind_risk,
        qr_content
    )

    # 🔄 UI refresh
    status_var.set("Status: Drone Approved ✅")
    load_pending_list()
    show_empty_detail()
