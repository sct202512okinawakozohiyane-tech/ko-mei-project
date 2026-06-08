import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
QUESTIONS_DIR = BASE_DIR / "questions" / "approved"
MAX_QUESTIONS = 200


def load_questions():
    questions = []
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                questions.append(json.load(f))
        except json.JSONDecodeError as e:
            print(f"[警告] {path.name} の読み込みに失敗しました: {e}")
    return questions


def show_pseudo_code(code):
    print("\n---- 擬似コード ----")
    for line in code.split("\n"):
        print(line)
    print("--------------------")


def ask_question(number, total, q):
    print(f"\n{'='*40}")
    print(f"問題 {number}/{total}  [{q.get('id', '')}]")
    print(f"{'='*40}")
    print(q["question"])

    pseudo_code = q.get("pseudo_code", "").strip()
    if pseudo_code:
        show_pseudo_code(pseudo_code)

    print()
    for key in ["A", "B", "C", "D"]:
        print(f"  {key}: {q['choices'][key]}")

    while True:
        answer = input("\n答えを入力してください (A/B/C/D): ").strip().upper()
        if answer in ("A", "B", "C", "D"):
            break
        print("A, B, C, D のいずれかを入力してください。")

    correct = q["answer"].strip().upper()
    if answer == correct:
        print("\n正解です！")
        is_correct = True
    else:
        print(f"\n不正解です。正解は {correct} です。")
        is_correct = False

    print(f"\n解説: {q['explanation']}")
    input("\nEnter キーで次へ...")
    return is_correct


def main():
    print("基本情報技術者試験 アルゴリズム練習")
    print("問題フォルダ:", QUESTIONS_DIR)

    questions = load_questions()
    if not questions:
        print("問題ファイルが見つかりませんでした。")
        return

    count = min(MAX_QUESTIONS, len(questions))
    selected = random.sample(questions, count)

    score = 0
    for i, q in enumerate(selected, start=1):
        if ask_question(i, count, q):
            score += 1

    print(f"\n{'='*40}")
    print(f"結果: {score} / {count} 問正解")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
