import sqlite3  # sqlite3 is built into Python, no install needed
import os

# Name of our database file - will be created automatically
DB_FILE = "sports_shield.db"

def get_connection():
    # This opens (or creates) the database file
    # check_same_thread=False allows Flask to use it from multiple requests
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # This makes results behave like dictionaries
    return conn

def init_db():
    # This runs once when app starts - creates our tables if they don't exist
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: stores info about every video we have protected
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS protected_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,       -- original name like "match_clip.mp4"
            protected_filename TEXT NOT NULL,      -- stamped version name
            watermark_id TEXT NOT NULL UNIQUE,     -- unique stamp ID we generated
            owner_name TEXT NOT NULL,              -- who uploaded it
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table 2: stores every stolen/fake video we detected
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_url TEXT,                        -- URL where stolen video was found
            detection_type TEXT NOT NULL,          -- either "stolen" or "fake"
            confidence REAL,                       -- how sure we are (0 to 100)
            matched_watermark_id TEXT,             -- which original video it matches
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dmca_generated INTEGER DEFAULT 0       -- 0 = no, 1 = yes
        )
    """)

    conn.commit()  # Save the changes
    conn.close()   # Close connection

def save_protected_video(original_filename, protected_filename, watermark_id, owner_name):
    # Save a newly protected video into database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO protected_videos 
        (original_filename, protected_filename, watermark_id, owner_name)
        VALUES (?, ?, ?, ?)
    """, (original_filename, protected_filename, watermark_id, owner_name))
    conn.commit()
    conn.close()

def get_all_protected_videos():
    # Get list of all protected videos (for dashboard)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM protected_videos ORDER BY upload_time DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]  # Convert to list of dicts

def save_detection(video_url, detection_type, confidence, matched_watermark_id=None):
    # Save a new detection (stolen or fake video found)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections 
        (video_url, detection_type, confidence, matched_watermark_id)
        VALUES (?, ?, ?, ?)
    """, (video_url, detection_type, confidence, matched_watermark_id))
    detection_id = cursor.lastrowid  # Get the ID of just-inserted row
    conn.commit()
    conn.close()
    return detection_id

def mark_dmca_generated(detection_id):
    # Update record to say DMCA notice was generated for this detection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE detections SET dmca_generated=1 WHERE id=?", (detection_id,))
    conn.commit()
    conn.close()

def get_all_detections():
    # Get all detections for dashboard
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM detections ORDER BY detected_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    # Get summary numbers for dashboard cards
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM protected_videos")
    total_protected = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM detections WHERE detection_type='stolen'")
    total_stolen = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM detections WHERE detection_type='fake'")
    total_fake = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM detections WHERE dmca_generated=1")
    total_dmca = cursor.fetchone()["total"]

    conn.close()
    return {
        "total_protected": total_protected,
        "total_stolen": total_stolen,
        "total_fake": total_fake,
        "total_dmca": total_dmca
    }
