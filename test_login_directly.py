import sqlite3
import bcrypt

DB_PATH = "mydatabase.db"


def test_login_flow():
    """Test the exact login flow from login.py"""

    username = "admin"
    password = "admin123"

    print("🔐 Testing login flow...\n")
    print(f"Username: {username}")
    print(f"Password: {password}\n")

    # Open database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Query (same as in login.py)
    cur.execute(
        "SELECT name, role, password_hash FROM authorizers WHERE username=?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        print("❌ User not found in database")
        return False

    name, role, pw_hash = row

    print(f"✅ User found:")
    print(f"   Name: {name}")
    print(f"   Role: {role}")
    print(f"   Password hash type: {type(pw_hash)}")
    print(f"   Password hash length: {len(pw_hash) if pw_hash else 0}")

    # Check hash format
    if isinstance(pw_hash, str):
        print(f"   Hash is STRING (needs to be BYTES)")
        print(f"   First 20 chars: {pw_hash[:20]}")
        pw_hash = pw_hash.encode()  # Convert to bytes
    elif isinstance(pw_hash, bytes):
        print(f"   Hash is BYTES ✅")
        print(f"   First 20 bytes: {pw_hash[:20]}")
    else:
        print(f"   ⚠️  Unexpected hash type: {type(pw_hash)}")

    print("\n🔍 Checking password...")

    # Check password (same as in login.py)
    try:
        password_bytes = password.encode()
        result = bcrypt.checkpw(password_bytes, pw_hash)

        if result:
            print("✅ PASSWORD CORRECT - Login should work!")
            return True
        else:
            print("❌ PASSWORD INCORRECT")

            # Try to debug
            print("\n🔧 Debugging:")
            print(f"   Input password bytes: {password_bytes}")
            print(f"   Stored hash: {pw_hash}")

            # Try creating a new hash to compare
            new_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            print(f"   New hash for comparison: {new_hash}")
            print(f"   New hash check: {bcrypt.checkpw(password_bytes, new_hash)}")

            return False

    except Exception as e:
        print(f"❌ Error during password check: {e}")
        print(f"   Exception type: {type(e)}")
        return False


def check_database_encoding():
    """Check how the database stores password_hash"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(authorizers)")
    columns = cur.fetchall()

    print("\n📋 Authorizers table structure:")
    for col in columns:
        print(f"   {col[1]}: {col[2]}")

    conn.close()


if __name__ == "__main__":
    check_database_encoding()
    print("\n" + "=" * 60 + "\n")

    success = test_login_flow()

    print("\n" + "=" * 60)
    if success:
        print("\n✅ Login test PASSED - Your credentials should work!")
        print("   If MAIN.py still fails, the issue is in the UI code")
    else:
        print("\n❌ Login test FAILED")
        print("   Need to fix the password hash in database")