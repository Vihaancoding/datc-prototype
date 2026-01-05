import bcrypt
import sqlite3

conn = sqlite3.connect("mydatabase.db")
cur = conn.cursor()

username = "admin"
password = "admin123"   # change later
name = "System Admin"
role = "ADMIN"

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

cur.execute("""
INSERT INTO authorizers (username, name, role, password_hash)
VALUES (?, ?, ?, ?)
""", (username, name, role, password_hash))

conn.commit()
conn.close()

print("✅ Admin user created")
print("Username:", username)
print("Password:", password)
