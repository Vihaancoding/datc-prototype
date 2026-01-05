import tkinter as tk


def create_root(r):
    """Create main window structure (hidden initially)"""
    r.title("DATC - Drone Authorization & Traffic Control")
    r.configure(bg="#2a2a2a")

    # DON'T set fullscreen yet - wait for login
    # r.attributes("-fullscreen", True)

    # Set a reasonable window size for when it shows
    r.geometry("1200x800")

    main = tk.Frame(r, bg="#2a2a2a")
    main.pack(fill="both", expand=True)

    status_var = tk.StringVar(value="Status: No drone selected")

    status_label = tk.Label(
        r,
        textvariable=status_var,
        font=("Menlo", 10),
        fg="white",
        bg="#444",
        anchor="w",
        padx=10
    )
    status_label.pack(side="bottom", fill="x")

    return main, status_var, status_label