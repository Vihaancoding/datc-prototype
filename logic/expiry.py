from db.db_helpers import get_db

def auto_suspend_expired():
    """
    Auto-suspend expired drone licenses.
    Does NOT affect REGISTERED or DENIED drones.
    Runs once at startup.
    """

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE drones
        SET
            qr_active = 0,
            state = 'EXPIRED'
        WHERE
            license_expiry IS NOT NULL
            AND DATE(license_expiry) < DATE('now')
            AND state NOT IN ('REGISTERED', 'DENIED', 'EXPIRED')
    """)

    affected = cur.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        print(f"[DATC] Auto-suspended {affected} expired license(s)")
