import tkinter as tk
from tkinter import messagebox
import bcrypt
from db.db_helpers import get_db
from logic.auth_context import CURRENT_AUTHORIZER


def login(root, on_success):
    """Show login dialog"""

    print("  Creating login toplevel...")
    win = tk.Toplevel(root)
    win.title("Authorizer Login")
    win.configure(bg="#2a2a2a")

    # Fixed size
    width = 350
    height = 250
    win.geometry(f"{width}x{height}")
    win.resizable(False, False)

    print("  Centering window...")
    # Center after window is created
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

    print("  Making modal...")
    # Make modal
    win.transient(root)
    win.lift()
    win.focus_force()
    win.grab_set()

    print("  Creating widgets...")
    # Title
    tk.Label(
        win,
        text="DATC Login",
        font=("Arial", 16, "bold"),
        bg="#2a2a2a",
        fg="white"
    ).pack(pady=15)

    # Default credentials hint (for testing)
    tk.Label(
        win,
        text="Default: admin / admin123",
        font=("Arial", 9),
        bg="#2a2a2a",
        fg="#888"
    ).pack(pady=(0, 10))

    # Username
    tk.Label(
        win,
        text="Username:",
        bg="#2a2a2a",
        fg="white",
        font=("Arial", 11)
    ).pack(anchor="w", padx=40)

    username_entry = tk.Entry(win, font=("Arial", 12), width=25)
    username_entry.pack(pady=(5, 15))

    # Password
    tk.Label(
        win,
        text="Password:",
        bg="#2a2a2a",
        fg="white",
        font=("Arial", 11)
    ).pack(anchor="w", padx=40)

    password_entry = tk.Entry(win, show="●", font=("Arial", 12), width=25)
    password_entry.pack(pady=(5, 20))

    def do_login():
        username = username_entry.get().strip()
        password = password_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password", parent=win)
            return

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT name, role, password_hash FROM authorizers WHERE username=?",
                (username,)
            )
            row = cur.fetchone()
            conn.close()

            if not row:
                messagebox.showerror("Error", "Invalid credentials", parent=win)
                password_entry.delete(0, tk.END)
                return

            name, role, pw_hash = row

            if not bcrypt.checkpw(password.encode(), pw_hash):
                messagebox.showerror("Error", "Invalid credentials", parent=win)
                password_entry.delete(0, tk.END)
                return

            # Success
            CURRENT_AUTHORIZER["name"] = name
            CURRENT_AUTHORIZER["role"] = role

            print(f"✅ Login successful: {name} ({role})")
            win.destroy()
            on_success()

        except Exception as e:
            messagebox.showerror("Error", f"Login failed: {e}", parent=win)
            print(f"❌ Login error: {e}")

    # Login button (Mac-style)
    login_btn = tk.Label(
        win,
        text="Login",
        font=("Arial", 12, "bold"),
        bg="#2e7d32",
        fg="white",
        padx=40,
        pady=8,
        cursor="hand2"
    )
    login_btn.pack(pady=10)
    login_btn.bind("<Button-1>", lambda e: do_login())

    # Hover effects
    login_btn.bind("<Enter>", lambda e: login_btn.config(bg="#388e3c"))
    login_btn.bind("<Leave>", lambda e: login_btn.config(bg="#2e7d32"))

    # Bind Enter key
    password_entry.bind("<Return>", lambda e: do_login())
    username_entry.bind("<Return>", lambda e: password_entry.focus_set())

    # Exit on close
    win.protocol("WM_DELETE_WINDOW", lambda: root.quit())

    print("  Setting focus...")
    # Force focus and update
    username_entry.focus_set()
    win.update()
    win.deiconify()
    win.lift()

    print("✅ Login window visible")