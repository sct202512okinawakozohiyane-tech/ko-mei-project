from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
from urllib.parse import quote
import sqlite3

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "toeic.db"


@app.route("/")
def index():
    return redirect(url_for("question"))


@app.route("/question")
def question():
    grammar_point = request.args.get("grammar_point", "").strip()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if grammar_point == "":
        where_clause = ""
        params = ()
    elif grammar_point == "未分類":
        where_clause = "WHERE (grammar_point IS NULL OR grammar_point = '')"
        params = ()
    else:
        where_clause = "WHERE grammar_point = ?"
        params = (grammar_point,)

    unanswered_filter = "id NOT IN (SELECT question_id FROM results)"
    if where_clause:
        unanswered_where = f"{where_clause} AND {unanswered_filter}"
    else:
        unanswered_where = f"WHERE {unanswered_filter}"

    cur.execute(f"""
        SELECT *
        FROM questions
        {unanswered_where}
        ORDER BY RANDOM()
        LIMIT 1
    """, params)
    row = cur.fetchone()

    if row is None:
        cur.execute(f"""
            SELECT *
            FROM questions
            {where_clause}
            ORDER BY RANDOM()
            LIMIT 1
        """, params)
        row = cur.fetchone()

    conn.close()

    return render_template(
        "question.html",
        question=row,
        grammar_point=grammar_point
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


@app.route("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(is_correct), 0) FROM results")
    total_count, correct_count = cur.fetchone()

    overall_accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

    cur.execute("""
        SELECT
            CASE
                WHEN q.grammar_point IS NULL OR q.grammar_point = '' THEN '未分類'
                ELSE q.grammar_point
            END AS grammar_point,
            COUNT(*) AS total,
            COALESCE(SUM(r.is_correct), 0) AS correct
        FROM results r
        JOIN questions q ON r.question_id = q.id
        GROUP BY grammar_point
        ORDER BY grammar_point
    """)

    grammar_stats = []
    for grammar_point, total, correct in cur.fetchall():
        accuracy = (correct / total * 100) if total > 0 else 0
        grammar_stats.append({
            "grammar_point": grammar_point,
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "practice_url": "/question?grammar_point=" + quote(grammar_point)
        })

    conn.close()

    return render_template(
        "history.html",
        total_count=total_count,
        correct_count=correct_count,
        overall_accuracy=overall_accuracy,
        grammar_stats=grammar_stats
    )


if __name__ == "__main__":
    app.run(debug=True)
