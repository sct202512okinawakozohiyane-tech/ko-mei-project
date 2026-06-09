from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "toeic.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
SELECT *
FROM questions
ORDER BY id DESC
LIMIT 1
""")

row = cur.fetchone()

print(row)

conn.close()
