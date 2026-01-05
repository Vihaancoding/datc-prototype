import tkinter as tk
from db.db_helpers import fetch_drone_company
import config

PLACEHOLDER_TEXT = "Enter Drone ID"

def setup_search_ui(r, status_var, update_status, open_selected_drone):
    search_var = tk.StringVar()

    def search_and_open_drone():
        drone_id = search_var.get().strip()
        if not drone_id or drone_id == PLACEHOLDER_TEXT:
            update_status("Enter a valid Drone ID", "red")
            return

        company = fetch_drone_company(drone_id)
        if not company:
            update_status("Drone not found", "red")
            return

        config.Companysel = company
        open_selected_drone(drone_id)
        update_status(f"Drone {drone_id} opened", "green")

    def open_search_dialog():
        win = tk.Toplevel(r)
        win.title("Search Drone")
        win.geometry("420x160")
        win.configure(bg="#2a2a2a")
        win.transient(r)
        win.grab_set()

        tk.Label(
            win, text="Enter Drone ID",
            bg="#2a2a2a", fg="white",
            font=("Menlo", 11)
        ).pack(pady=(20, 10))

        entry = tk.Entry(win, textvariable=search_var, font=("Menlo", 11), width=40)
        entry.pack()
        entry.focus_set()

        entry.bind("<Return>", lambda e: (search_and_open_drone(), win.destroy()))

        tk.Button(
            win, text="Search",
            font=("Menlo", 10),
            command=lambda: (search_and_open_drone(), win.destroy())
        ).pack(pady=15)

    # Menu
    menubar = tk.Menu(r)
    r.config(menu=menubar)
    search_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Search", menu=search_menu)
    search_menu.add_command(label="Search Drone by ID", command=open_search_dialog)
    r.bind("<Control-f>", lambda e: open_search_dialog())

    return search_and_open_drone
