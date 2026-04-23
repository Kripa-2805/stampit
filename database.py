import sqlite3
import bcrypt  # encrypts passwords — never stores plain text

DB_FILE = "stampit.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # USERS TABLE — stores registered users with encrypted passwords
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,   -- NEVER plain text, always bcrypt hash
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PROTECTED VIDEOS — each video tied to a user_id
    # user A can NEVER see user B's videos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS protected_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_filename TEXT NOT NULL,
            protected_filename TEXT NOT NULL,
            watermark_id TEXT NOT NULL UNIQUE,
            owner_name TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # DETECTIONS — stolen/fake videos found, also tied to user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_url TEXT,
            detection_type TEXT NOT NULL,
            confidence REAL,
            matched_watermark_id TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dmca_generated INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

# ── USER AUTH FUNCTIONS ──

def create_user(username, email, password):
    """
    Registers new user.
    bcrypt.hashpw() encrypts the password before saving.
    Salt = random noise added so same passwords have different hashes.
    """
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),   # convert string to bytes
        bcrypt.gensalt()            # generate random salt
    ).decode("utf-8")               # convert bytes back to string for storage

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id, None
    except sqlite3.IntegrityError as e:
        conn.close()
        if "username" in str(e):
            return None, "Username already taken"
        elif "email" in str(e):
            return None, "Email already registered"
        return None, "Registration failed"

def verify_user(username, password):
    """
    Checks login credentials.
    bcrypt.checkpw() compares entered password with stored hash.
    Returns user dict if correct, None if wrong.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    # checkpw compares plain password with encrypted hash safely
    if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return dict(user)
    return None

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# ── VIDEO FUNCTIONS — ALL FILTERED BY user_id ──

def save_protected_video(user_id, original_filename, protected_filename, watermark_id, owner_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO protected_videos
        (user_id, original_filename, protected_filename, watermark_id, owner_name)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, original_filename, protected_filename, watermark_id, owner_name))
    conn.commit()
    conn.close()

def get_user_protected_videos(user_id):
    # WHERE user_id = ? → user sees ONLY their own videos
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM protected_videos WHERE user_id=? ORDER BY upload_time DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_detection(user_id, video_url, detection_type, confidence, matched_watermark_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections
        (user_id, video_url, detection_type, confidence, matched_watermark_id)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, video_url, detection_type, confidence, matched_watermark_id))
    detection_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return detection_id

def get_user_detections(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM detections WHERE user_id=? ORDER BY detected_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_dmca_generated(detection_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE detections SET dmca_generated=1 WHERE id=?", (detection_id,))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as t FROM protected_videos WHERE user_id=?", (user_id,))
    total_protected = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM detections WHERE user_id=? AND detection_type='stolen'", (user_id,))
    total_stolen = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM detections WHERE user_id=? AND detection_type='fake'", (user_id,))
    total_fake = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM detections WHERE user_id=? AND dmca_generated=1", (user_id,))
    total_dmca = cursor.fetchone()["t"]
    conn.close()
    return {
        "total_protected": total_protected,
        "total_stolen": total_stolen,
        "total_fake": total_fake,
        "total_dmca": total_dmca
    }
