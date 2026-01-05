# ==============================
# IMPORTS
# ==============================
print("📦 Loading imports...")

print("  - tkinter...")
import tkinter as tk
from tkinter import messagebox

print("  - PIL...")
from PIL import Image, ImageTk

print("  - os...")
import os

print("  - db_helpers...")
from db.db_helpers import get_db

print("  - approve...")
from actions.approve import approve_drone

print("  - deny...")
from actions.deny import deny_drone

print("  - ui.root...")
from ui.root import create_root

print("  - ui.search...")
from ui.search import setup_search_ui

print("  - ui.pending...")
from ui.pending import setup_pending_panel

print("  - ui.details...")
from ui.details import setup_details_panel

print("  - logic.expiry...")
from logic.expiry import auto_suspend_expired

print("  - logic.auth_context...")
from logic.auth_context import CURRENT_AUTHORIZER

print("  - ui.login...")
from ui.login import login

print("✅ Imports loaded")

# ==============================
# INITIALIZE ROOT WINDOW
# ==============================
print("🪟 Creating root window...")
r = tk.Tk()
r.withdraw()  # hide until everything is ready

print("🎨 Creating main window structure...")
# Create main window structure FIRST (before login)
main, status_var, status_label = create_root(r)

print("✅ Main window created")

# ==============================
# GLOBAL STATE
# ==============================
current_drone_id = None
auto_assign_var = tk.BooleanVar(value=True)  # AUTO mode default ON

# ==============================
# AUTHORIZATION INPUT STATE
# ==============================
airspace_var = tk.StringVar(value="CONTROLLED")
max_distance_var = tk.StringVar(value="3")
max_altitude_var = tk.StringVar(value="90")

# ==============================
# UI HELPERS
# ==============================
def update_status(msg, color="white"):
    """Update status bar with temporary message"""
    status_label.config(text=msg, fg=color)
    r.after(4000, lambda: status_label.config(text="Ready", fg="white"))

# ==============================
# TOGGLE LICENSE STATUS
# ==============================
def toggle_license_status(drone_id, state_dict, btn_label, status_label, drone_state):
    """Toggle drone license active/suspended status"""
    # Block if still registered (not yet approved)
    if drone_state.lower() == "registered":
        messagebox.showwarning(
            "Action Blocked",
            "This drone is only REGISTERED.\n"
            "Approval is required before activating or suspending the license."
        )
        return

    # Toggle qr_active
    state_dict["active"] = 1 - int(state_dict["active"])

    # Update database
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE drones SET qr_active = ? WHERE id = ?",
        (state_dict["active"], drone_id)
    )
    conn.commit()
    conn.close()

    # Determine new state
    new_state = "approved" if state_dict["active"] == 1 else "suspended"

    # Update UI elements
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
# MAC-STYLE BUTTON HELPER
# ==============================
def mac_button_pack(parent, text, command, bg, fg="white", padx=12, pady=6):
    """Create macOS-style button with hover effects"""
    btn = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Menlo", 11),
        padx=padx,
        pady=pady,
        anchor="center",
        cursor="hand2"
    )
    btn.pack(side="right", padx=10, pady=15)
    btn.bind("<Button-1>", lambda e: command())
    return btn

# ==============================
# ACTION BUTTON RENDERER
# ==============================
def render_action_buttons(state):
    """Render Approve/Deny buttons based on drone state"""
    # Clear existing buttons
    for w in action_bar.winfo_children():
        w.destroy()

    # Normalize state
    state = state.strip().lower()

    if state == "registered":
        mac_button_pack(
            action_bar,
            text="Approve",
            bg="#2ecc71",
            command=lambda: approve_drone(
                current_drone_id,
                pending_qr_map,
                auto_assign_var,
                airspace_var,
                max_distance_var,
                max_altitude_var,
                status_var,
                load_pending_list,
                show_empty_detail
            )
        )

        mac_button_pack(
            action_bar,
            text="Deny",
            bg="#e74c3c",
            command=lambda: deny_drone(
                current_drone_id,
                get_denial_flags(),
                status_var,
                load_pending_list,
                show_empty_detail
            )
        )

# ==============================
# DRONE DETAIL WINDOW
# ==============================
def open_selected_drone(drone_id):
    """Open detailed view for a specific drone"""
    import tkinter.font as tkfont
    import config

    # Define fonts
    FONT_BODY = tkfont.Font(root=r, family="Menlo", size=11)
    FONT_BUTTON = tkfont.Font(root=r, family="Arial", size=11, weight="bold")

    # Create window
    win = tk.Toplevel(r)
    win.configure(bg="#2a2a2a")

    # Set fullscreen (macOS-safe)
    w, h = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{w}x{h}+0+0")
    win.transient(r)
    win.lift()
    win.focus_force()

    # Fetch drone data
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
        win.destroy()
        messagebox.showerror("Error", f"Drone {drone_id} not found")
        return

    name, dtype, year, model, manu, qr_active, qr_link, expiry, db_state = row

    # Handle missing QR link
    if not qr_link:
        win.destroy()
        messagebox.showerror(
            "Error",
            f"Drone {drone_id} has no QR code.\nThis drone may not be properly registered."
        )
        return

    config.Companysel = name

    # Extract QR ID
    stripped_id = qr_link.replace("http://localhost:5000/verify?id=", "")

    # Mutable state
    license_state = {"active": qr_active}

    # Determine effective state
    if db_state.lower() == "registered":
        effective_state = "registered"
    else:
        effective_state = "approved" if int(qr_active) == 1 else "suspended"

    # Display labels
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

    # Status label
    status_label_win = tk.Label(
        win,
        text=f"License Status: {'✅ LICENSE VALID' if qr_active else '❌ LICENSE SUSPENDED'}",
        font=FONT_BODY,
        bg="#2a2a2a",
        fg="white"
    )
    status_label_win.place(x=25, y=200)

    # QR Image
    qr_path = f"qr_codes/{stripped_id}.png"
    if os.path.exists(qr_path):
        try:
            img = Image.open(qr_path).resize((180, 180))
            photo = ImageTk.PhotoImage(img)
            qr = tk.Label(win, image=photo, bg="#2a2a2a")
            qr.image = photo
            qr.place(x=25, y=240)
        except Exception as e:
            print(f"Error loading QR image: {e}")
            # Show placeholder text instead
            tk.Label(
                win,
                text="QR Code\nNot Available",
                font=("Menlo", 10),
                bg="#2a2a2a",
                fg="#888",
                width=20,
                height=10
            ).place(x=25, y=240)
    else:
        print(f"QR image not found: {qr_path}")
        tk.Label(
            win,
            text="QR Code\nNot Available",
            font=("Menlo", 10),
            bg="#2a2a2a",
            fg="#888",
            width=20,
            height=10
        ).place(x=25, y=240)

    win.update_idletasks()

    def mac_button(parent, text, x, y, command, width=16):
        """Create positioned button with hover effects"""
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
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg="#505050"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#3a3a3a"))
        return btn

    # Toggle button
    toggle_btn = mac_button(
        win,
        "Deactivate License" if license_state["active"] else "Activate License",
        800,
        600,
        lambda: toggle_license_status(
            drone_id,
            license_state,
            toggle_btn,
            status_label_win,
            effective_state
        )
    )

    if effective_state.lower() != "approved":
        toggle_btn.config(
            text="Awaiting Approval",
            fg="#bbbbbb",
            bg="#555555"
        )

    def on_company_close():
        """Handle window close - reopen company view"""
        win.destroy()
        from ui.Company import open_companywindow
        open_companywindow(r, open_selected_drone)

    win.protocol("WM_DELETE_WINDOW", on_company_close)
    win.update_idletasks()

# ==============================
# SETUP UI PANELS (BUILD EVERYTHING BEFORE SHOWING)
# ==============================
print("🔧 Setting up UI panels...")

# MAC-STYLE BUTTON HELPER (moved up before use)
def mac_button_pack(parent, text, command, bg, fg="white", padx=12, pady=6):
    """Create macOS-style button with hover effects"""
    btn = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Menlo", 11),
        padx=padx,
        pady=pady,
        anchor="center",
        cursor="hand2"
    )
    btn.pack(side="right", padx=10, pady=15)
    btn.bind("<Button-1>", lambda e: command())
    return btn

# ACTION BUTTON RENDERER (moved up before use)
def render_action_buttons(state):
    """Render Approve/Deny buttons based on drone state"""
    # Clear existing buttons
    for w in action_bar.winfo_children():
        w.destroy()

    # Normalize state
    state = state.strip().lower()

    if state == "registered":
        mac_button_pack(
            action_bar,
            text="Approve",
            bg="#2ecc71",
            command=lambda: approve_drone(
                current_drone_id,
                pending_qr_map,
                auto_assign_var,
                airspace_var,
                max_distance_var,
                max_altitude_var,
                status_var,
                load_pending_list,
                show_empty_detail
            )
        )

        mac_button_pack(
            action_bar,
            text="Deny",
            bg="#e74c3c",
            command=lambda: deny_drone(
                current_drone_id,
                get_denial_flags(),
                status_var,
                load_pending_list,
                show_empty_detail
            )
        )

# Search functionality
print("🔍 Setting up search UI...")
search_and_open_drone = setup_search_ui(
    r, status_var, update_status, open_selected_drone
)

# Details panel (right side)
print("📋 Setting up details panel...")
detail_container, action_bar, show_empty_detail, load_drone_details, get_denial_flags = setup_details_panel(
    main,
    status_var,
    status_label,
    render_action_buttons
)

# Pending drones callback
def on_pending_select(listbox, pending_map, status_var, status_label):
    """Handle selection from pending drones list"""
    global current_drone_id

    if not listbox.curselection():
        return

    selected = listbox.get(listbox.curselection())
    current_drone_id = pending_map[selected]

    status_var.set("Status: Drone selected")
    status_label.update_idletasks()

    load_drone_details(current_drone_id)

# Pending drones panel (left side)
print("📝 Setting up pending panel...")
pending_map, pending_qr_map, load_pending_list = setup_pending_panel(
    main, status_var, status_label, on_pending_select
)

print("✅ All panels loaded")

# ==============================
# STARTUP TASKS
# ==============================
print("⏰ Running auto-suspend check...")
auto_suspend_expired()

print("✅ UI components loaded")

# Login success callback
def on_login_success():
    """Called after successful login"""
    print("✅ Login successful, showing main window")
    r.attributes("-fullscreen", True)
    r.deiconify()
    r.lift()
    r.focus_force()

# Start mainloop first
def show_login():
    print("🔐 Showing login window...")
    login(r, on_login_success)

# Show login after 100ms (lets mainloop start)
r.after(100, show_login)

print("🚀 Starting mainloop...")
r.mainloop()