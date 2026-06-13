import sqlite3

conn = sqlite3.connect("data/toeic.db")

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part INTEGER,
    question_text TEXT,
    choice_a TEXT,
    choice_b TEXT,
    choice_c TEXT,
    choice_d TEXT,
    correct_answer TEXT,
    explanation TEXT,
    difficulty TEXT,
    grammar_point TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    user_answer TEXT,
    is_correct INTEGER,
    answered_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("DB initialized")
