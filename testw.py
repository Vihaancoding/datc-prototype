from db.db_helpers import get_db

conn = get_db()
cur = conn.cursor()
cur.execute("SELECT id, name, state FROM drones")
print(cur.fetchall())
conn.close()
