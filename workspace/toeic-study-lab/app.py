from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
import sqlite3

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "toeic.db"


@app.route("/")
def index():
    return redirect(url_for("question"))


@app.route("/question")
def question():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM questions
        ORDER BY RANDOM()
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    return render_template(
        "question.html",
        question=row
    )


@app.route("/answer", methods=["POST"])
def answer():
    question_id = request.form.get("question_id")
    user_answer = request.form.get("user_answer")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM questions
        WHERE id = ?
    """, (question_id,))

    row = cur.fetchone()

    correct_answer = row[7]
    explanation = row[8]

    is_correct = 1 if user_answer == correct_answer else 0

    cur.execute("""
        INSERT INTO results (
            question_id,
            user_answer,
            is_correct
        )
        VALUES (?, ?, ?)
    """, (question_id, user_answer, is_correct))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        question=row,
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        explanation=explanation
    )


if __name__ == "__main__":
    app.run(debug=True)
