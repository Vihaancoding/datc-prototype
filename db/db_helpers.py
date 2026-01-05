
import sqlite3

DB_PATH = "mydatabase.db"

def get_db():
    return sqlite3.connect(
        DB_PATH,
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

def get_pending_drones():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, qr_content
        FROM drones
        WHERE state='REGISTERED'
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows
