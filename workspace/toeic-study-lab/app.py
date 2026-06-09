from flask import Flask, render_template
from pathlib import Path
import sqlite3

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "toeic.db"


@app.route("/")
def question():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM questions
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    conn.close()

    return render_template(
        "question.html",
        question=row
    )


if __name__ == "__main__":
    app.run(debug=True)
