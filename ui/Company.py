import tkinter as tk
import os

import config # ✅ Import from config.py
from Dropdown import dropdownn  # ✅ No circular import


is_Company_open = False  # ✅ Global flag
from db.db_helpers import get_db








def fetch_drones_from_db():
    """Fetch drone IDs where name matches `Companysel`."""
    print("DEBUG: Fetching drones from database...")
    connection = get_db()


    cursor = connection.cursor()

    cursor.execute("SELECT id FROM drones WHERE name = ?", (config.Companysel,))
    rows = cursor.fetchall()
    connection.close()

    print(f"DEBUG: Fetched {len(rows)} drones.")
    return rows
def fetch_company_details(company_name):
    """Fetch company details from the database."""
    connection = get_db()

    cursor = connection.cursor()

    # ✅ Search for the company
    cursor.execute("SELECT name, year_founded, location FROM companies WHERE name = ?", (company_name,))
    result = cursor.fetchone()
    connection.close()

    return result if result else None

def open_companywindow(r, open_selected_drone):
    """Opens the company selection window."""

    global is_Company_open

    if is_Company_open:
        print(f"DEBUG: Closing previous company window.")
        close_Company(Company, r)  # ✅ Close the previous window before opening a new one

    is_Company_open = True

    print("DEBUG: Opening company window.")
    Company = tk.Toplevel(r)
    Company.title(f"{config.Companysel} Drones")
    Company.state("zoomed")
    Company.configure(bg="#2a2a2a")




    # ✅ Display Company Name
    nameLabel = tk.Label(Company, text=f"{config.Companysel}", font=("Consolas", 14), fg="#FFFFFF", bg="#2a2a2a")
    nameLabel.place(x=10, y=10)

    dropdownn(Company, open_selected_drone)

    # ✅ Fetch the list of drones
    drones_list = fetch_drones_from_db()
    num_drones = len(drones_list)  # ✅ Count the number of drones safely

    owned_label = tk.Label(Company, text=f"Total Number of Drones: {num_drones}", font=("Consolas", 10), fg="#FFFFFF",
                           bg="#2a2a2a")
    owned_label.place(x=15, y=150)

    company_details = fetch_company_details(config.Companysel)


    if company_details:
        name, year, location = company_details
        details_text = f"Company:{name}\nFounded:{year}\nLocation:{location}"
    else:
        details_text = "Company details not found."

    # ✅ Label to Show Company Details
    details_label = tk.Label(Company, text=details_text, font=("Consolas", 10), fg="white", bg="#2a2a2a")
    details_label.place(x=10, y=170)

    logo_path = f"logos/{config.Companysel}.png"  # Ensure PNG format


    def go_back_to_main(Company, r):
        """Closes the company window and returns to the main page."""
        close_Company(Company, r)
        r.deiconify()  # ✅ Show the main window again

    # ✅ Create the main menu
    drone1 = tk.Menu(r)
    Company.config(menu=drone1)

    # ✅ Create a submenu
    filemenu1 = tk.Menu(drone1, tearoff=0)
    filemenu1.add_command(label='Back to Main', font=("Consolas", 10), command=lambda: go_back_to_main(Company, r))
    # ✅ Add filemenu as a dropdown under 'File'

    drone1.add_cascade(label="Options", menu=filemenu1)

    if os.path.exists(logo_path):
        logo_img = tk.PhotoImage(file=logo_path)

        # ✅ Display Image
        logo_label = tk.Label(Company, image=logo_img, bg="#2a2a2a")
        logo_label.image = logo_img  # ✅ Keep a reference to avoid garbage collection
        logo_label.place(x=10, y=50)
    else:
        print(f"WARNING: No logo found for {config.Companysel} at {logo_path}")

    #check_for_updates()
    # ✅ Run again after 1000ms (1 sec)
    Company.wait_visibility()
    Company.after(600, r.withdraw)
    #check_for_updates()




    Company.protocol("WM_DELETE_WINDOW", lambda: close_Company(Company, r))

def close_Company(Company, r):
    """Restores main window after closing the company window."""
    global is_Company_open

    if r.winfo_exists() and r.state() == "withdrawn":
        r.state("zoomed")
        r.deiconify()
        r.wait_visibility()
        Company.destroy()
        print("DEBUG: Main window restored.")
        global Companysel
        Companysel = None

    is_Company_open = False


