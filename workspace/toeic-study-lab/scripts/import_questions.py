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
    choice_translations = q.get("choice_translations", {})
    choice_explanations = q.get("choice_explanations", {})

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
            grammar_point,
            question_translation,
            choice_a_translation,
            choice_b_translation,
            choice_c_translation,
            choice_d_translation,
            explanation_a,
            explanation_b,
            explanation_c,
            explanation_d
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        q.get("question_translation"),
        choice_translations.get("A"),
        choice_translations.get("B"),
        choice_translations.get("C"),
        choice_translations.get("D"),
        choice_explanations.get("A"),
        choice_explanations.get("B"),
        choice_explanations.get("C"),
        choice_explanations.get("D"),
    ))

conn.commit()
conn.close()

print(f"{len(questions)} questions imported from {JSON_PATH}")
