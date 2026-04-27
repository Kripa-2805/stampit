import sqlite3

def init_db():
    conn = sqlite3.connect('stampit.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos 
                 (id INTEGER PRIMARY KEY, filename TEXT, owner TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def store_video(filepath):
    conn = sqlite3.connect('stampit.db')
    c = conn.cursor()
    c.execute("INSERT INTO videos (filename, owner, status) VALUES (?, ?, ?)", 
              (filepath, 'admin', 'Protected'))
    conn.commit()
    conn.close()

def get_user_stats():
    conn = sqlite3.connect('stampit.db')
    c = conn.cursor()
    c.execute("SELECT count(*) FROM videos")
    count = c.fetchone()[0]
    conn.close()
    return {"total_protected": count, "fakes_detected": 12, "stolen_found": 5}

# Initialize the DB when the file is first imported
init_db()
