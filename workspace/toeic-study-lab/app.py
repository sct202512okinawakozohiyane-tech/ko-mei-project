from flask import Flask, render_template, request, url_for
from pathlib import Path
from urllib.parse import quote
import sqlite3

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "toeic.db"

MODE_LABELS = {
    "all": "全問題",
    "category": "分野別",
    "incorrect": "間違えた問題",
    "unanswered": "未回答問題",
    "weak_category": "苦手分野",
}


def build_category_where(grammar_point):
    """grammar_point指定からWHERE句とパラメータを組み立てる。"""
    if grammar_point == "未分類":
        return "WHERE (grammar_point IS NULL OR grammar_point = '')", ()
    return "WHERE grammar_point = ?", (grammar_point,)


def fetch_question(cur, where_clause, params):
    """未回答の問題を優先し、なければwhere_clauseの範囲からランダムに1問返す。"""
    unanswered_filter = "id NOT IN (SELECT question_id FROM results)"
    if where_clause:
        unanswered_where = f"{where_clause} AND {unanswered_filter}"
    else:
        unanswered_where = f"WHERE {unanswered_filter}"

    cur.execute(f"""
        SELECT * FROM questions
        {unanswered_where}
        ORDER BY RANDOM()
        LIMIT 1
    """, params)
    row = cur.fetchone()

    if row is None:
        cur.execute(f"""
            SELECT * FROM questions
            {where_clause}
            ORDER BY RANDOM()
            LIMIT 1
        """, params)
        row = cur.fetchone()

    return row


def fetch_weak_grammar_point(cur):
    """正答率が最も低いgrammar_point（回答数0は除外）を返す。データがなければNone。"""
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
        HAVING total > 0
        ORDER BY (CAST(correct AS FLOAT) / total) ASC
        LIMIT 1
    """)
    row = cur.fetchone()
    return row[0] if row else None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/question")
def question():
    mode = request.args.get("mode", "").strip()
    grammar_point = request.args.get("grammar_point", "").strip()

    if not mode:
        mode = "category" if grammar_point else "all"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    row = None
    message = None

    if mode == "all":
        row = fetch_question(cur, "", ())

    elif mode == "category":
        if not grammar_point:
            message = "練習する文法項目（grammar_point）を指定してください。"
        else:
            where_clause, params = build_category_where(grammar_point)
            row = fetch_question(cur, where_clause, params)

    elif mode == "incorrect":
        cur.execute("""
            SELECT * FROM questions
            WHERE id IN (SELECT DISTINCT question_id FROM results WHERE is_correct = 0)
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        if row is None:
            message = "間違えた問題はまだありません。"

    elif mode == "unanswered":
        cur.execute("""
            SELECT * FROM questions
            WHERE id NOT IN (SELECT question_id FROM results)
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        if row is None:
            message = "未回答の問題はありません。すべて回答済みです。"

    elif mode == "weak_category":
        weak_point = fetch_weak_grammar_point(cur)
        if weak_point is None:
            message = "苦手分野を判定するための回答データがまだありません。まずは問題に回答してください。"
        else:
            grammar_point = weak_point
            where_clause, params = build_category_where(grammar_point)
            row = fetch_question(cur, where_clause, params)

    else:
        message = f"不明な出題モードです: {mode}"

    conn.close()

    return render_template(
        "question.html",
        question=row,
        grammar_point=grammar_point,
        mode=mode,
        mode_label=MODE_LABELS.get(mode, mode),
        message=message
    )


@app.route("/answer", methods=["POST"])
def answer():
    question_id = request.form.get("question_id")
    user_answer = request.form.get("user_answer")
    mode = request.form.get("mode", "")
    grammar_point = request.form.get("grammar_point", "")

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

    next_url_params = {}
    if mode:
        next_url_params["mode"] = mode
    if grammar_point:
        next_url_params["grammar_point"] = grammar_point
    next_url = url_for("question", **next_url_params)

    return render_template(
        "result.html",
        question=row,
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        explanation=explanation,
        next_url=next_url
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
            "practice_url": "/question?mode=category&grammar_point=" + quote(grammar_point)
        })

    conn.close()

    return render_template(
        "history.html",
        total_count=total_count,
        correct_count=correct_count,
        overall_accuracy=overall_accuracy,
        grammar_stats=grammar_stats
    )


@app.route("/grammar_points")
def grammar_points():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            CASE
                WHEN grammar_point IS NULL OR grammar_point = '' THEN '未分類'
                ELSE grammar_point
            END AS grammar_point,
            COUNT(*) AS total
        FROM questions
        GROUP BY grammar_point
    """)
    question_counts = {gp: total for gp, total in cur.fetchall()}

    cur.execute("""
        SELECT
            CASE
                WHEN q.grammar_point IS NULL OR q.grammar_point = '' THEN '未分類'
                ELSE q.grammar_point
            END AS grammar_point,
            COUNT(*) AS answered,
            COALESCE(SUM(r.is_correct), 0) AS correct
        FROM results r
        JOIN questions q ON r.question_id = q.id
        GROUP BY grammar_point
    """)
    answer_stats = {gp: (answered, correct) for gp, answered, correct in cur.fetchall()}

    conn.close()

    grammar_point_list = []
    for gp, total in sorted(question_counts.items()):
        answered, correct = answer_stats.get(gp, (0, 0))
        accuracy = (correct / answered * 100) if answered > 0 else None
        grammar_point_list.append({
            "grammar_point": gp,
            "question_count": total,
            "answered_count": answered,
            "correct_count": correct,
            "accuracy": accuracy,
            "practice_url": "/question?mode=category&grammar_point=" + quote(gp)
        })

    return render_template("grammar_points.html", grammar_point_list=grammar_point_list)


if __name__ == "__main__":
    app.run(debug=True)
