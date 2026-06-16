import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "toeic.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(questions)")
columns = [row[1] for row in cur.fetchall()]

if "grammar_category" in columns:
    print("grammar_category column already exists")
else:
    cur.execute("ALTER TABLE questions ADD COLUMN grammar_category TEXT")
    conn.commit()
    print("grammar_category column added")

conn.close()
