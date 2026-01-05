import sqlite3
import tkinter as tk
from config import Companysel  # ✅ Import from config.py instead of MAIN.py

def fetch_rows_from_database():
    """Fetch drone IDs from the database where name is the selected company."""
    print("DEBUG: Fetching rows from database...")  # ✅ Debug print
    connection = sqlite3.connect('mydatabase.db')
    cursor = connection.cursor()

    # ✅ Use parameterized query
    cursor.execute("SELECT id FROM drones WHERE name = ?", (Companysel,))
    rows = cursor.fetchall()
    connection.close()

    print(f"DEBUG: Fetched {len(rows)} rows.")  # ✅ Debug print
    return rows

def dropdownn(Company, open_selected_drone):
    """Create a dropdown with available drones."""
    rows = fetch_rows_from_database()
    options = [row[0] for row in rows] if rows else ["No Drones Available"]
    print(f"DEBUG: Dropdown options: {options}")  # ✅ Debug print

    variable = tk.StringVar()
    variable.set("Select a drone")

    dropdown = tk.OptionMenu(Company, variable, *options, command=lambda value: open_selected_drone(value))
    dropdown.config(width=15, highlightcolor="#2a2a2a", bd="0")
    dropdown.pack(pady=30)
    print("DEBUG: Dropdown created and packed.")  # ✅ Debug print
