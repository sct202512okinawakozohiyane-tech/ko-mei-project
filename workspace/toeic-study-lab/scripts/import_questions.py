import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "toeic.db"
JSON_PATH = BASE_DIR / "questions" / "approved" / "questions.json"

with open(JSON_PATH, encoding="utf-8") as f:
    questions = json.load(f)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for q in questions:
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
            difficulty,
            grammar_point
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        q["part"],
        q["question_text"],
        q["choice_a"],
        q["choice_b"],
        q["choice_c"],
        q["choice_d"],
        q["correct_answer"],
        q["explanation"],
        q["difficulty"],
        q["grammar_point"],
    ))

conn.commit()
conn.close()

print(f"{len(questions)} questions imported from {JSON_PATH}")
