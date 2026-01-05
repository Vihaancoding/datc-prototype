# ==============================
# IMPORTS
# ==============================
import tkinter as tk
from tkinter import messagebox
import sqlite3
from PIL import Image, ImageTk
from db.db_helpers import get_db, fetch_drone_company, get_pending_drones

# ==============================
# CONSTANTS
# ==============================
DB_PATH = "mydatabase.db"
PLACEHOLDER_TEXT = "Enter Drone ID"

# ==============================
# DATABASE HELPERS
# ==============================
def get_db():
    return sqlite3.connect(
        "mydatabase.db",
        timeout=10,
        isolation_level=None
    )




def fetch_drone_company(drone_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM drones WHERE id = ?", (drone_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


# ==============================
# UI HELPERS
# ==============================
def update_status(msg, color="white"):
    status_label.config(text=msg, fg=color)
    r.after(4000, lambda: status_label.config(text="Ready", fg="white"))


def on_entry_click(event):
    if search_entry.get() == PLACEHOLDER_TEXT:
        search_entry.delete(0, tk.END)
        search_entry.config(fg="black")


def on_focus_out(event):
    if not search_entry.get().strip():
        search_entry.insert(0, PLACEHOLDER_TEXT)
        search_entry.config(fg="grey")


# ==============================
# SEARCH LOGIC
# ==============================
def search_and_open_drone():
    drone_id = search_var.get().strip()

    if not drone_id or drone_id == PLACEHOLDER_TEXT:
        update_status("Enter a valid Drone ID", "red")
        return

    company = fetch_drone_company(drone_id)
    if not company:
        update_status("Drone not found", "red")
        return

    import config
    config.Companysel = company

    open_selected_drone(drone_id)



    update_status(f"Drone {drone_id} opened", "green")


# ==============================
# ADMIN PASSCODE DIALOG
# ==============================
def admin_passcode_dialog():
    dialog = tk.Toplevel(r)
    dialog.title("Admin Passcode")


    # 🔑 CRITICAL: force dialog to NOT be fullscreen
    dialog.attributes("-fullscreen", False)
    dialog.geometry("300x150")

    dialog.configure(bg="#2a2a2a")
    dialog.resizable(False, False)

    tk.Label(
        dialog, text="Enter Admin Passcode",
        bg="#2a2a2a", fg="white",
        font=("Menlo", 11)
    ).pack(pady=10)

    entry = tk.Entry(dialog, show="*", font=("Menlo", 11))
    entry.pack()

    result = {"value": None}

    def mac_button_pack(parent, text, command, pady=10):
        btn = tk.Label(
            parent,
            text=text,
            fg="white",
            bg="#2e7d32",  # green
            font=("Arial", 11, "bold"),
            padx=20,
            pady=6,
            anchor="center"
        )

        btn.pack(pady=pady)
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def submit():
        result["value"] = entry.get()
        dialog.destroy()

    mac_button_pack(dialog, "Submit", submit)

    dialog.grab_set()
    dialog.wait_window()
    return result["value"]

def toggle_license_status(drone_id, state_dict, btn_label, status_label, drone_state):
    # 🔒 Block ONLY if still registered
    if drone_state.lower() == "registered":
        messagebox.showwarning(
            "Action Blocked",
            "This drone is only REGISTERED.\n"
            "Approval is required before activating or suspending the license."
        )
        return

    # Toggle qr_active safely
    state_dict["active"] = 1 - int(state_dict["active"])

    # Update DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE drones SET qr_active = ? WHERE id = ?",
        (state_dict["active"], drone_id)
    )
    conn.commit()
    conn.close()

    # Derive new effective state
    new_state = "approved" if state_dict["active"] == 1 else "suspended"

    # Update UI
    btn_label.config(
        text="Deactivate License" if new_state == "approved" else "Activate License"
    )

    status_label.config(
        text=(
            "License Status: ✅ APPROVED"
            if new_state == "approved"
            else "License Status: ❌ SUSPENDED"
        )
    )

    messagebox.showinfo(
        "Success",
        f"Drone {drone_id} license {new_state.upper()}."
    )



# ==============================
# DRONE WINDOW
# ==============================
def open_selected_drone(drone_id):
    global Companysel
    global win
    global mac_button
    import tkinter.font as tkfont

    # ===== Global Fonts (macOS-safe) =====
    FONT_TITLE = tkfont.Font(
        root=r,
        family="Menlo",
        size=12,
        weight="bold"
    )

    FONT_BODY = tkfont.Font(
        root=r,
        family="Menlo",
        size=11

    )

    FONT_BUTTON = tkfont.Font(
        root=r,
        family="Arial",  # safest for macOS buttons
        size=11,
        weight="bold"
    )

    win = tk.Toplevel(r)
    win.configure(bg="#2a2a2a")

    # macOS-safe fullscreen
    w, h = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{w}x{h}+0+0")
    win.transient(r)
    win.lift()
    win.focus_force()



    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, Type, year, model, Manufacturer,
               qr_active, qr_content, license_expiry, state
        FROM drones WHERE id=?
    """, (drone_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return

    name, dtype, year, model, manu, qr_active, qr_link, expiry, db_state = row

    Companysel = name


    stripped_id = qr_link.replace("http://localhost:5000/verify?id=", "")

    # Mutable state (correct)
    license_state = {"active": qr_active}

    if db_state.lower() == "registered":
        effective_state = "registered"
    else:
        effective_state = "approved" if int(qr_active) == 1 else "suspended"

    labels = [
        f"Drone No: {drone_id}",
        f"Company: {name}",
        f"Drone ID: {stripped_id}",
        f"Manufacturer: {manu}",
        f"Year: {year}",
        f"License Expiry: {expiry}"
    ]

    for i, txt in enumerate(labels):
        tk.Label(
            win,
            text=txt,
            font=FONT_BODY,
            bg="#2a2a2a",
            fg="white"
        ).place(x=25, y=30 + i * 25)

    status_label = tk.Label(
        win,
        text=f"License Status: {'✅ LICENSE VALID' if qr_active else '❌ LICENSE SUSPENDED'}",
        font=FONT_BODY,
        bg="#2a2a2a",
        fg="white"
    )
    status_label.place(x=25, y=200)

    # QR Image (safe)
    img = Image.open(f"qr_codes/{stripped_id}.png").resize((180, 180))
    photo = ImageTk.PhotoImage(img)
    qr = tk.Label(win, image=photo, bg="#2a2a2a")
    qr.image = photo
    qr.place(x=25, y=240)

    win.update_idletasks()
    win.update()

    def mac_button(parent, text, x, y, command, width=16):
        btn = tk.Label(
            parent,
            text=text,
            fg="white",
            bg="#3a3a3a",
            font=("Arial", 11, "bold"),
            width=width,
            height=1,
            anchor="center",
            cursor="hand2"
        )

        btn.place(x=x, y=y)

        # Click
        btn.bind("<Button-1>", lambda e: command())

        # Hover effects
        btn.bind("<Enter>", lambda e: btn.config(bg="#505050"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#3a3a3a"))

        return btn

    # Toggle button (mac-safe)
    toggle_btn = mac_button(
        win,
        "Deactivate License" if license_state["active"] else "Activate License",
        800,
        600,
        lambda: toggle_license_status(
            drone_id,
            license_state,
            toggle_btn,
            status_label,
            effective_state  # 👈 PASS STATE
        )
    )
    if effective_state.lower() != "approved":

        toggle_btn.config(
            text="Awaiting Approval",
            fg="#bbbbbb",
            bg="#555555"
        )

    def on_company_close():
        win.destroy()
        from ui.Company import open_companywindow
        open_companywindow(r, open_selected_drone)  # 👈 open another window AFTER close

    win.protocol("WM_DELETE_WINDOW", on_company_close)


    # Force paint (macOS required)
    win.update_idletasks()
    win.update()

# ==============================
# MAIN WINDOW
# ==============================
r = tk.Tk()
r.title("DATC")
r.configure(bg="#2a2a2a")
r.attributes("-fullscreen", True)

main = tk.Frame(r, bg="#2a2a2a")
main.pack(fill="both", expand=True)

# ==============================
# GLOBAL STATE
# ==============================
current_drone_id = None
auto_assign_var = tk.BooleanVar(value=True)  # AUTO mode default ON

def compute_capability(
    motor_thrust,
    motor_count,
    takeoff_weight,
    max_payload,
    battery_wh,
    cruise_power,
    wind_limit
):
    # DEV fallbacks
    motor_thrust = motor_thrust or 1.0
    motor_count = motor_count or 4
    takeoff_weight = takeoff_weight or 2.5
    max_payload = max_payload or 0.3
    battery_wh = battery_wh or 50.0
    cruise_power = cruise_power or 200.0
    wind_limit = wind_limit or 10

    # Thrust margin
    thrust_margin = (motor_thrust * motor_count) / takeoff_weight
    if thrust_margin < 1.8:
        thrust_state = "UNSAFE"
    elif thrust_margin <= 2.2:
        thrust_state = "MARGINAL"
    else:
        thrust_state = "SAFE"

    # Endurance
    max_time_min = (battery_wh / cruise_power) * 60
    safe_time = max_time_min * 0.75
    if safe_time < 10:
        endurance_state = "FAIL"
    elif safe_time <= 15:
        endurance_state = "LIMITED"
    else:
        endurance_state = "PASS"

    # Payload ratio
    payload_ratio = max_payload / takeoff_weight

    # Wind risk
    if wind_limit < 15:
        wind_risk = "HIGH"
    elif wind_limit < 25:
        wind_risk = "MEDIUM"
    else:
        wind_risk = "LOW"

    return (
        thrust_margin,
        thrust_state,
        safe_time,
        endurance_state,
        payload_ratio,
        wind_risk
    )

# ==============================
# AUTHORIZATION INPUT STATE
# ==============================
airspace_var = tk.StringVar(value="CONTROLLED")
max_distance_var = tk.StringVar(value="3")
max_altitude_var = tk.StringVar(value="90")



# ==============================
# LEFT PANEL – PENDING DRONES
# ==============================

pending_map = {}
pending_qr_map = {}

def load_pending_list():
    pending_list.delete(0, tk.END)
    pending_map.clear()
    pending_qr_map.clear()

    for drone_id, name, qr_content in get_pending_drones():
        label = f"ID {drone_id} — {name}"
        pending_list.insert(tk.END, label)
        pending_map[label] = drone_id
        pending_qr_map[drone_id] = qr_content

def on_pending_select(event):
    global current_drone_id

    if not pending_list.curselection():
        return

    selected = pending_list.get(pending_list.curselection())
    current_drone_id = pending_map[selected]

    # 🔴 FORCE IMMEDIATE STATUS UPDATE
    status_var.set("Status: Drone selected")
    status_label.update_idletasks()   # <- CRITICAL LINE
    print("STATUS TEXT =", status_var.get())

    load_drone_details(current_drone_id)


left_panel = tk.Frame(main, bg="#1f1f1f", width=300)
left_panel.pack(side="left", fill="y")
left_panel.pack_propagate(False)

tk.Label(
    left_panel,
    text="Pending Approvals",
    bg="#1f1f1f",
    fg="white",
    font=("Menlo", 13, "bold")
).pack(pady=15)

pending_list = tk.Listbox(
    left_panel,
    bg="#2a2a2a",
    fg="white",
    selectbackground="#444",
    font=("Menlo", 10)
)
pending_list.pack(fill="both", expand=True, padx=10, pady=10)
pending_list.bind("<<ListboxSelect>>", on_pending_select)

load_pending_list()

# ==============================
# RIGHT PANEL
# ==============================
right_panel = tk.Frame(main, bg="#2a2a2a")
right_panel.pack(side="right", fill="both", expand=True)

tk.Label(
    right_panel,
    text="Drone Management System",
    bg="#2a2a2a",
    fg="white",
    font=("Arial", 18, "bold")
).pack(pady=20)

detail_container = tk.Frame(right_panel, bg="#2a2a2a")
detail_container.pack(fill="both", expand=True, padx=30, pady=30)

action_bar = tk.Frame(right_panel, bg="#1a1a1a", height=70)
action_bar.pack(side="bottom", fill="x")
action_bar.pack_propagate(False)

# ==============================
# STATUS BAR (CREATE ONCE)
# ==============================
status_var = tk.StringVar(value="Status: No drone selected")

status_label = tk.Label(
    action_bar,
    textvariable=status_var,
    bg="#1a1a1a",
    fg="white",
    font=("Menlo", 11)
)
status_label.pack(side="left", padx=20)

# ==============================
# MAC-STYLE BUTTON
# ==============================
def mac_button(parent, text, bg, command):
    btn = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg="white",
        font=("Menlo", 11),
        padx=16,
        pady=6,
        cursor="hand2"
    )
    btn.pack(side="right", padx=12, pady=15)
    btn.bind("<Button-1>", lambda e: command())
    return btn

# ==============================
# EMPTY DETAIL VIEW
# ==============================
def show_empty_detail():
    for w in detail_container.winfo_children():
        w.destroy()

    for w in action_bar.winfo_children():
        if w is not status_label:
            w.destroy()

    status_var.set("Status: No drone selected")

    tk.Label(
        detail_container,
        text="Select a drone from Pending Approvals",
        font=("Menlo", 14),
        bg="#2a2a2a",
        fg="#888"
    ).place(relx=0.5, rely=0.5, anchor="center")

show_empty_detail()

# ==============================
# LOAD DRONE DETAILS
# ==============================
def load_drone_details(drone_id):
    for w in detail_container.winfo_children():
        w.destroy()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            name,
            Type,
            year,
            model,
            Manufacturer,
            license_expiry,
            state,
            takeoff_weight,
            max_payload,
            motor_thrust,
            motor_count,
            battery_wh,
            cruise_power,
            wind_limit,
            thrust_margin,
            safe_flight_time,
            capability_status
        FROM drones
        WHERE id=?
    """, (drone_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return

    (
        name,
        dtype,
        year,
        model,
        manu,
        expiry,
        state,
        takeoff_weight,
        max_payload,
        motor_thrust,
        motor_count,
        battery_wh,
        cruise_power,
        wind_limit,
        thrust_margin,
        safe_flight_time,
        capability_status
    ) = row
    # ===== DEV MODE FALLBACK VALUES =====
    DEV_MODE = True

    if DEV_MODE:
        motor_thrust = motor_thrust or 1.0  # kg per motor (very low)
        motor_count = motor_count or 4
        takeoff_weight = takeoff_weight or 2.5  # kg
        battery_wh = battery_wh or 50.0  # Wh
        cruise_power = cruise_power or 200.0  # W
        max_payload = max_payload or 0.3  # kg
        wind_limit = wind_limit or 10  # km/h
    # ===================================

    thrust_margin = (motor_thrust * motor_count) / takeoff_weight
    if thrust_margin < 1.8:
        Thrust_state = "REJECTED, Insufficient thrust margin"


    elif 1.8 <= thrust_margin <= 2.2:
        Thrust_state = "RESTRICTED, Marginal thrust margin – limited operations only"


    else:  # thrust_margin > 2.2
        Thrust_state = "APPROVED, Adequate thrust margin"

    max_time_min = (battery_wh / cruise_power) * 60
    safe_time = max_time_min * 0.75

    if safe_time < 10:
        endurance_state = "RESTRICTED"
        endurance_reason = "Short-range only"


    elif safe_time >= 10 and safe_time <= 15:

        endurance_state = "LIMITED"
        endurance_reason = "Moderate endurance – operational limits apply"

    else:
        endurance_state = "NORMAL"
        endurance_reason = "Normal operations permitted"

    payload_ratio = (max_payload / takeoff_weight) * 100

    if wind_limit < 15:
        wind_risk = "HIGH"
    elif wind_limit < 25:
        wind_risk = "MODERATE"
    else:
        wind_risk = "LOW"

    fields = [
        ("Drone ID", drone_id),
        ("Company", name),
        ("Type", dtype),
        ("Model", model),
        ("Manufacturer", manu),
        ("Year", year),
        ("License Expiry", expiry),
        ("Thrust Margin", thrust_margin),
        ("Thrust Margin Safety", Thrust_state ),
        ("Max flight time", max_time_min),
        ("Safe flight time", safe_time),
        ("Endurance", endurance_state, endurance_reason),
        ("Payload Utilization", payload_ratio),
        ("Wind Risk", wind_risk)



    ]

    for i, (label, value, *_) in enumerate(fields):

        tk.Label(
            detail_container,
            text=f"{label}:",
            font=("Menlo", 11, "bold"),
            bg="#2a2a2a",
            fg="white"
        ).grid(row=i, column=0, sticky="w", pady=6)

        tk.Label(
            detail_container,
            text=value,
            font=("Menlo", 11),
            bg="#2a2a2a",
            fg="#ccc"
        ).grid(row=i, column=1, sticky="w", pady=6)
    # ===============================
    # DENIAL REASON FIELD
    # ===============================
    global denial_reason_box

    tk.Label(
        detail_container,
        text="Reason for Denial (required if denying):",
        font=("Menlo", 11, "bold"),
        bg="#2a2a2a",
        fg="white"
    ).grid(row=len(fields) + 1, column=0, sticky="w", pady=(20, 5), columnspan=2)

    denial_reason_box = tk.Text(
        detail_container,
        height=4,
        width=50,
        font=("Menlo", 10),
        bg="#1f1f1f",
        fg="white",
        insertbackground="white",
        wrap="word"
    )
    denial_reason_box.grid(
        row=len(fields) + 2,
        column=0,
        columnspan=2,
        sticky="w"
    )

    state_clean = state.strip().upper()

    if state_clean == "REGISTERED":
        status_var.set("Status: Pending Review")
    elif state_clean == "APPROVED":
        status_var.set("Status: Drone Approved ✅")
    elif state_clean == "DENIED":
        status_var.set("Status: Drone Denied ❌")
    else:
        status_var.set(f"Status: {state_clean}")

    # 🔴 FORCE REDRAW
    status_label.update_idletasks()

    render_action_buttons(state)

# ==============================
# ACTION BUTTONS
# ==============================
def render_action_buttons(state):
    for w in action_bar.winfo_children():
        if w is not status_label:
            w.destroy()

    if state.lower() == "registered":
        mac_button(action_bar, "Approve", "#2ecc71", approve_drone)
        mac_button(action_bar, "Deny", "#e74c3c", deny_drone)

# ===============================
# EMAIL FUNCTIONS
# ===============================
from email.message import EmailMessage
import smtplib
import os

def send_approval_email(
    to_email,
    company,
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

Non-compliance with the above limits may result in suspension or revocation
of authorization.

Regards,
DATC Authority
Unmanned Aircraft Regulatory Division
""")

    # 📎 Attach QR code image
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


# 📧 Send denial email (no attachment)
def send_denial_email(to_email, company, dtype, model, manu, year, submitted_at, reason):
    if not to_email:
        print("WARNING: No email provided for denial")
        return

    msg = EmailMessage()
    msg["Subject"] = "Drone Registration Application Denied"
    msg["From"] = "authority@datc.gov"
    msg["To"] = to_email

    msg.set_content(f"""
Dear {company},

Your drone registration application has been DENIED.

Application details:
• Company: {company}
• Drone Type: {dtype}
• Model: {model}
• Manufacturer: {manu}
• Year: {year}
• Submitted on: {submitted_at}

Reason for denial:
{reason}

No operational license or QR authorization has been issued.

You may submit a fresh application after correcting the issues.

Regards,
DATC Authority
""")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("datcdroneregistery@gmail.com", "yyiv tgth qljf mbwg")
        server.send_message(msg)






# ==============================
# APPROVE / DENY
# ==============================
# imports
# get_db()
# email functions

def auto_assign_authorization(
    thrust_margin,
    thrust_state,
    safe_time,
    endurance_state,
    payload_ratio,
    wind_risk
):
    # 🚫 Hard safety fails
    if thrust_state != "SAFE" or endurance_state != "PASS":
        return "RESTRICTED", 1.0, 60

    # 🟡 Base airspace from wind
    if wind_risk == "HIGH":
        airspace = "RESTRICTED"
    elif wind_risk == "MEDIUM":
        airspace = "CONTROLLED"
    else:
        airspace = "OPEN"

    # 🟡 Base distance from safe flight time
    if safe_time < 10:
        max_dist = 1.0
    elif safe_time < 20:
        max_dist = 3.0
    elif safe_time < 40:
        max_dist = 8.0
    else:
        max_dist = 15.0

    # ⚠ Payload penalty
    if payload_ratio > 0.85:
        max_dist *= 0.5

    # 🟢 Thrust bonus
    if thrust_margin > 1.8:
        max_dist *= 1.2

    # ✈ Altitude tied to airspace
    max_alt = {
        "RESTRICTED": 60,
        "CONTROLLED": 90,
        "OPEN": 120
    }[airspace]

    return airspace, round(max_dist, 1), max_alt



def approve_drone():
    global current_drone_id

    if not current_drone_id:
        return

    # ===============================
    # 1️⃣ FETCH DATA REQUIRED
    # ===============================

    conn = get_db()
    cur = conn.cursor()

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
        WHERE id=?
    """, (current_drone_id,))


    row = cur.fetchone()
    conn.close()

    if not row:
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

    # ===============================
    # ASSIGN AUTHORIZATION
    # ===============================
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


    # ===============================
    # 3️⃣ UPDATE DATABASE (ONCE)
    # ===============================
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE drones
        SET
            state='APPROVED',
            qr_active=1,
            airspace_type=?,
            max_distance_km=?,
            max_altitude_m=?,
            assignment_mode=?
        WHERE id=?
    """, (airspace, max_dist, max_alt, assignment_mode, current_drone_id))

    conn.commit()
    conn.close()

    # ===============================
    # 4️⃣ SEND APPROVAL EMAIL
    # ===============================
    send_approval_email(
        email,
        company,
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

    # ===============================
    # 5️⃣ UPDATE UI
    # ===============================
    status_var.set("Status: Drone Approved ✅")
    load_pending_list()
    show_empty_detail()



def deny_drone():
    global current_drone_id

    if not current_drone_id:
        return

    # 1️⃣ OPEN DB
    conn = get_db()
    cur = conn.cursor()   # 🔑 THIS LINE WAS MISSING / BROKEN

    # 2️⃣ FETCH APPLICATION DATA (NO DRONE ID)
    cur.execute("""
        SELECT email, name, Type, model, Manufacturer, year, submitted_at
        FROM drones
        WHERE id=?
    """, (current_drone_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return

    email, company, dtype, model, manu, year, submitted_at = row

    reason = denial_reason_box.get("1.0", "end").strip()


    send_denial_email(
        email,
        company,
        dtype,
        model,
        manu,
        year,
        submitted_at,
        reason
    )



    # 4️⃣ DELETE QR FILE (IF IT EXISTS)
    cur.execute("""
        SELECT qr_content
        FROM drones
        WHERE id=?
    """, (current_drone_id,))
    qr_row = cur.fetchone()

    if qr_row and qr_row[0]:
        qr_path = f"qr_codes/{qr_row[0]}.png"
        if os.path.exists(qr_path):
            os.remove(qr_path)
            print("DEBUG: Deleted QR image:", qr_path)

    # 5️⃣ DELETE DB RECORD
    cur.execute("DELETE FROM drones WHERE id=?", (current_drone_id,))
    conn.commit()
    conn.close()

    # 6️⃣ UPDATE UI
    status_var.set("Status: Drone Denied ❌")
    current_drone_id = None
    load_pending_list()
    show_empty_detail()



# ===============================
# ACTION BUTTON RENDERER
# ===============================
def mac_button_pack(parent, text, command, bg, fg="white", padx=12, pady=6):
    btn = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Menlo", 11),
        padx=padx,
        pady=pady,
        anchor="center"
    )

    btn.pack(side="right", padx=10, pady=15)
    btn.bind("<Button-1>", lambda e: command())

    return btn


def render_action_buttons(state):
    # Clear existing buttons
    for w in action_bar.winfo_children():
        w.destroy()

    # Normalize state once
    state = state.strip().lower()

    if state == "registered":
        mac_button_pack(
            action_bar,
            text="Approve",
            bg="#2ecc71",
            command=approve_drone
        )

        mac_button_pack(
            action_bar,
            text="Deny",
            bg="#e74c3c",
            command=deny_drone
        )



#==============================================
#              SEARCH FUNCTION
#==============================================
# ---- GLOBAL SEARCH VARIABLE (DEFINE ONCE) ----
search_var = tk.StringVar()


# ---- SEARCH DIALOG ----
def open_search_dialog():
    global search_var

    win = tk.Toplevel(r)
    win.title("Search Drone")
    win.geometry("420x160")
    win.configure(bg="#2a2a2a")
    win.transient(r)
    win.grab_set()

    tk.Label(
        win,
        text="Enter Drone ID",
        bg="#2a2a2a",
        fg="white",
        font=("Menlo", 11)
    ).pack(pady=(20, 10))

    entry = tk.Entry(
        win,
        textvariable=search_var,
        font=("Menlo", 11),
        width=40
    )
    entry.pack()
    entry.focus_set()

    def run_search():
        drone_id = search_var.get().strip()
        if not drone_id:
            status_label.config(text="⚠ Enter a Drone ID to search")
            return

        search_and_open_drone()
        win.destroy()

    entry.bind("<Return>", lambda e: run_search())

    tk.Button(
        win,
        text="Search",
        font=("Menlo", 10),
        command=run_search
    ).pack(pady=15)


# ---- ACTION BAR (RIGHT PANEL BOTTOM) ----
action_bar = tk.Frame(right_panel, bg="#1a1a1a", height=80)
action_bar.pack(side="bottom", fill="x")
action_bar.pack_propagate(False)



status_label = tk.Label(
    action_bar,
    textvariable=status_var,
    bg="#1a1a1a",
    fg="white",
    font=("Menlo", 11)
)




# ---- MENU BAR ----
menubar = tk.Menu(r)
r.config(menu=menubar)

search_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Search", menu=search_menu)

search_menu.add_command(
    label="Search Drone by ID",
    command=open_search_dialog
)

# Optional shortcut
r.bind("<Control-f>", lambda e: open_search_dialog())


# ---- STATUS BAR ----
status_label = tk.Label(
    r,
    text="Ready",
    font=("Menlo", 10),
    fg="white",
    bg="#444",
    anchor="w",
    padx=10
)
status_label.pack(side="bottom", fill="x")


print("DEBUG: Running mainloop...")
r.mainloop()