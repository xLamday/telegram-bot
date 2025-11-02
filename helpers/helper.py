import sqlite3
import random, string, sqlite3, time
from config import DB_FILE, CODE_VALIDITY


# === HELPERS ===
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def save_code(code, admin_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO pending_codes (code, admin_id, created_at) VALUES (?, ?, ?)", (code, admin_id, int(time.time())))
    conn.commit()
    conn.close()

def check_code(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT admin_id, created_at FROM pending_codes WHERE code=?", (code,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None

    admin_id, created_at = row
    if int(time.time()) - created_at > CODE_VALIDITY:
        # codice scaduto
        remove_code(code)
        return None
    return admin_id

def remove_code(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM pending_codes WHERE code=?", (code,))
    conn.commit()
    conn.close()
