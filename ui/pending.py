import tkinter as tk
from db.db_helpers import get_pending_drones

def setup_pending_panel(main, status_var, status_label, on_select):
    pending_map = {}
    pending_qr_map = {}

    left = tk.Frame(main, bg="#1f1f1f", width=300)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    tk.Label(
        left, text="Pending Approvals",
        bg="#1f1f1f", fg="white",
        font=("Menlo", 13, "bold")
    ).pack(pady=15)

    lst = tk.Listbox(
        left, bg="#2a2a2a", fg="white",
        selectbackground="#444", font=("Menlo", 10)
    )
    lst.pack(fill="both", expand=True, padx=10, pady=10)

    def load_pending_list():
        lst.delete(0, tk.END)
        pending_map.clear()
        pending_qr_map.clear()
        for drone_id, name, qr in get_pending_drones():
            label = f"ID {drone_id} — {name}"
            lst.insert(tk.END, label)
            pending_map[label] = drone_id
            pending_qr_map[drone_id] = qr

    lst.bind("<<ListboxSelect>>", lambda e: on_select(
        lst, pending_map, status_var, status_label
    ))

    load_pending_list()
    return pending_map, pending_qr_map, load_pending_list
