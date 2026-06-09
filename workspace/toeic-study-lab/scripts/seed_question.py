from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "toeic.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
INSERT INTO questions (
    part,
    question_text,
    choice_a,
    choice_b,
    choice_c,
    choice_d,
    correct_answer,
    explanation,
    difficulty
)
VALUES (
    5,
    'The manager suggested that the report _____ by Friday.',
    'submit',
    'submitted',
    'be submitted',
    'submitting',
    'C',
    'suggest that の後は原形。受動態なので be submitted。',
    'standard'
)
""")

conn.commit()
conn.close()

print("Question inserted")
