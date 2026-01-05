import os
from tkinter import messagebox

from db.db_helpers import get_db
from emailer.notifications import send_denial_email
from logic.auth_context import CURRENT_AUTHORIZER, current_timestamp
from datetime import datetime



def deny_drone(
    current_drone_id,
    denial_flags,
    status_var,
    load_pending_list,
    show_empty_detail
):
    # ✅ Collect selected denial reasons
    selected_reasons = [
        reason for reason, var in denial_flags.items() if var.get()
    ]

    if not selected_reasons:
        messagebox.showerror(
            "Denial Blocked",
            "You must select at least one denial reason before denying."
        )
        return

    if not current_drone_id:
        return

    conn = get_db()
    cur = conn.cursor()

    # 🔍 Fetch drone details
    cur.execute("""
        SELECT email, name, Type, model, Manufacturer, year, submitted_at, qr_content
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
        dtype,
        model,
        manu,
        year,
        submitted_at,
        qr_content
    ) = row

    # ✅ SINGLE-SOURCE VARIABLES (use everywhere)
    denied_by = CURRENT_AUTHORIZER["name"]
    denied_role = CURRENT_AUTHORIZER["role"]
    denied_at = current_timestamp()

    # 🗂 Store denial metadata
    cur.execute("""
        UPDATE drones
        SET denied_by = ?, denied_at = ?
        WHERE id = ?
    """, (
        denied_by,
        denied_at,
        current_drone_id
    ))

    # 📝 Build reason text
    reason_text = "\n".join(f"- {r}" for r in selected_reasons)

    # 📧 Send denial email
    send_denial_email(
        email,
        company,
        dtype,
        model,
        manu,
        year,
        submitted_at,
        reason_text,
        denied_by=denied_by,
        denied_role=denied_role,
        denied_at=denied_at
    )

    # 🗑 Delete QR image
    if qr_content:
        qr_path = f"qr_codes/{qr_content}.png"
        if os.path.exists(qr_path):
            os.remove(qr_path)

    # ❌ Delete drone record
    cur.execute("DELETE FROM drones WHERE id = ?", (current_drone_id,))
    conn.commit()
    conn.close()

    # 🔄 Update UI
    status_var.set("Status: Drone Denied ❌")
    load_pending_list()
    show_empty_detail()
