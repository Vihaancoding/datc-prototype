import sqlite3
import bcrypt

DB_PATH = "mydatabase.db"


def check_authorizers():
    """Check what's in the authorizers table"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='authorizers'")
    if not cur.fetchone():
        print("❌ authorizers table doesn't exist!")
        conn.close()
        return False

    # Check contents
    cur.execute("SELECT id, username, name, role FROM authorizers")
    rows = cur.fetchall()

    print(f"\n📋 Found {len(rows)} authorizer(s) in database:\n")
    for row in rows:
        print(f"  ID: {row[0]}")
        print(f"  Username: {row[1]}")
        print(f"  Name: {row[2]}")
        print(f"  Role: {row[3]}")
        print()

    conn.close()
    return len(rows) > 0


def create_admin_user():
    """Create a fresh admin user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS authorizers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Delete existing admin if any
    cur.execute("DELETE FROM authorizers WHERE username = 'admin'")

    # Create new admin with bcrypt hash
    password = "admin123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    cur.execute("""
        INSERT INTO authorizers (username, password_hash, name, role)
        VALUES (?, ?, ?, ?)
    """, ("admin", password_hash, "Rahul Verma", "Senior Authorizer"))

    conn.commit()
    conn.close()

    print("✅ Created admin user:")
    print("   Username: admin")
    print("   Password: admin123")
    print("   Role: Senior Authorizer\n")


def test_login():
    """Test if login works"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT name, role, password_hash FROM authorizers WHERE username=?", ("admin",))
    row = cur.fetchone()
    conn.close()

    if not row:
        print("❌ Admin user not found!")
        return False

    name, role, pw_hash = row
    test_password = "admin123"

    if bcrypt.checkpw(test_password.encode(), pw_hash):
        print("✅ Login test PASSED")
        print(f"   Name: {name}")
        print(f"   Role: {role}")
        return True
    else:
        print("❌ Login test FAILED - password doesn't match")
        return False


if __name__ == "__main__":
    print("🔍 Checking authorizers table...\n")

    has_users = check_authorizers()

    if not has_users:
        print("⚠️  No authorizers found. Creating admin user...\n")
        create_admin_user()
    else:
        response = input("Do you want to recreate the admin user? (y/n): ")
        if response.lower() == 'y':
            print("\n🔧 Recreating admin user...\n")
            create_admin_user()

    print("\n🧪 Testing login credentials...\n")
    test_login()