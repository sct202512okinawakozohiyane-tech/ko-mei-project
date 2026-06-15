import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "toeic.db"

NEW_COLUMNS = [
    "question_translation",
    "choice_a_translation",
    "choice_b_translation",
    "choice_c_translation",
    "choice_d_translation",
    "explanation_a",
    "explanation_b",
    "explanation_c",
    "explanation_d",
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(questions)")
columns = [row[1] for row in cur.fetchall()]

for column in NEW_COLUMNS:
    if column in columns:
        print(f"{column} column already exists")
    else:
        cur.execute(f"ALTER TABLE questions ADD COLUMN {column} TEXT")
        print(f"{column} column added")

conn.commit()
conn.close()
