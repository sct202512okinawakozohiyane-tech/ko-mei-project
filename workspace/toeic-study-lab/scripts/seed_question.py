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
VALUES (
    5,
    'The manager suggested that the report _____ by Friday.',
    'submit',
    'submitted',
    'be submitted',
    'submitting',
    'C',
    'suggest that の後は原形。受動態なので be submitted。',
    'standard',
    '仮定法現在（suggest that構文）と受動態',
    'マネージャーはその報告書を金曜日までに提出するよう提案した。',
    '提出する',
    '提出された',
    '提出される',
    '提出していること',
    '能動態の原形。reportは提出する側ではなく提出される側なので不可。',
    '過去分詞のみでは動詞として機能せず、文が成立しない。',
    'suggest that構文では動詞は原形になり、reportは提出される側なので受動態の原形が正しい。',
    '動名詞であり、suggest that構文の動詞の位置には文法的に不適切。'
)
""")

conn.commit()
conn.close()

print("Question inserted")
