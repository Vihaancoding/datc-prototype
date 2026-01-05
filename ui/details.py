import tkinter as tk
from db.db_helpers import get_db


def setup_details_panel(main, status_var, status_label, render_action_buttons):
    # ==============================
    # RIGHT PANEL

    # ==============================
    denial_flags = {}

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
    # EMPTY DETAIL VIEW
    # ==============================
    def show_empty_detail():
        for w in detail_container.winfo_children():
            w.destroy()

        for w in action_bar.winfo_children():
            w.destroy()

        status_var.set("Status: No drone selected")

        tk.Label(
            detail_container,
            text="Select a drone from Pending Approvals",
            font=("Menlo", 14),
            bg="#2a2a2a",
            fg="#888"
        ).place(relx=0.5, rely=0.5, anchor="center")

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
            motor_thrust = motor_thrust or 1.0
            motor_count = motor_count or 4
            takeoff_weight = takeoff_weight or 2.5
            battery_wh = battery_wh or 50.0
            cruise_power = cruise_power or 200.0
            max_payload = max_payload or 0.3
            wind_limit = wind_limit or 10
        # ===================================

        thrust_margin = (motor_thrust * motor_count) / takeoff_weight
        if thrust_margin < 1.8:
            thrust_state = "REJECTED, Insufficient thrust margin"
        elif 1.8 <= thrust_margin <= 2.2:
            thrust_state = "RESTRICTED, Marginal thrust margin – limited operations only"
        else:
            thrust_state = "APPROVED, Adequate thrust margin"

        max_time_min = (battery_wh / cruise_power) * 60
        safe_time = max_time_min * 0.75

        if safe_time < 10:
            endurance_state = "RESTRICTED"
            endurance_reason = "Short-range only"
        elif 10 <= safe_time <= 15:
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
            ("Thrust Margin Safety", thrust_state),
            ("Max flight time", max_time_min),
            ("Safe flight time", safe_time),
            ("Endurance", f"{endurance_state} — {endurance_reason}"),
            ("Payload Utilization (%)", payload_ratio),
            ("Wind Risk", wind_risk),
        ]

        for i, (label, value) in enumerate(fields):
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
        # DENIAL CHECKBOXES
        # ===============================
        denial_flags.clear()
        denial_flags.update({
            "Thrust margin not satisfactory": tk.BooleanVar(),
            "Endurance not satisfactory": tk.BooleanVar(),
            "Payload safety not satisfactory": tk.BooleanVar(),
            "Wind tolerance not satisfactory": tk.BooleanVar(),
        })

        tk.Label(
            detail_container,
            text="Denial Reasons (select at least one):",
            font=("Menlo", 11, "bold"),
            bg="#2a2a2a",
            fg="white"
        ).grid(row=len(fields) + 1, column=0, sticky="w", pady=(20, 5), columnspan=2)

        for i, (label, var) in enumerate(denial_flags.items()):
            tk.Checkbutton(
                detail_container,
                text=label,
                variable=var,
                bg="#2a2a2a",
                fg="white",
                selectcolor="#2a2a2a",
                activebackground="#2a2a2a"
            ).grid(
                row=len(fields) + 2 + i,
                column=0,
                sticky="w",
                columnspan=2
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

        status_label.update_idletasks()
        render_action_buttons(state)

    show_empty_detail()

    def get_denial_flags():
        return denial_flags

    return (
        detail_container,
        action_bar,
        show_empty_detail,
        load_drone_details,
        get_denial_flags
    )

