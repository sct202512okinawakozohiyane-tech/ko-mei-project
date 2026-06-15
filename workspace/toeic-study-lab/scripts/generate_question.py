import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "questions" / "generate_part5.txt"
PENDING_DIR = BASE_DIR / "questions" / "pending"

# コンテナ内（ko-meiコンテナ）からの実行を想定したデフォルト値。
# コンテナ外でローカルのOllamaを使う場合は、環境変数で上書きする。
#   OLLAMA_URL=http://localhost:11434/api/generate python scripts/generate_question.py
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL_NAME = os.environ.get("KOMEI_MODEL", "gemma4:e4b")

# (connectタイムアウト, readタイムアウト)
# stream=True で受信するため、トークンが届くたびにreadタイムアウトがリセットされる
REQUEST_TIMEOUT = (10, 600)

CHOICE_LETTERS = ["A", "B", "C", "D"]


def shuffle_choices(question_data):
    """choice_a〜d / choice_translations / choice_explanations をランダムな順序に
    並び替え、correct_answerをシャッフル後の位置に合わせて再設定する。

    LLM側の出力位置に依存せず、正解位置（A〜D）の分布を一様にするための後処理。
    不正なcorrect_answerの場合はNoneを返す。
    """

    if question_data.get("correct_answer") not in CHOICE_LETTERS:
        return None

    items = []
    for letter in CHOICE_LETTERS:
        items.append({
            "text": question_data.get(f"choice_{letter.lower()}", ""),
            "translation": question_data.get("choice_translations", {}).get(letter, ""),
            "explanation": question_data.get("choice_explanations", {}).get(letter, ""),
            "is_correct": letter == question_data["correct_answer"],
        })

    random.shuffle(items)

    choice_translations = {}
    choice_explanations = {}

    for new_letter, item in zip(CHOICE_LETTERS, items):
        question_data[f"choice_{new_letter.lower()}"] = item["text"]
        choice_translations[new_letter] = item["translation"]
        choice_explanations[new_letter] = item["explanation"]
        if item["is_correct"]:
            question_data["correct_answer"] = new_letter

    question_data["choice_translations"] = choice_translations
    question_data["choice_explanations"] = choice_explanations

    return question_data


def load_prompt():
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def extract_json_text(response_text):
    text = response_text.strip()

    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def generate_one(prompt):
    """Ollamaに1問分の生成をリクエストし、パース済みのdictを返す。
    失敗時はエラー内容を表示してNoneを返す。"""

    print(f"[INFO] Ollamaに問題生成をリクエストします（model={MODEL_NAME}, url={OLLAMA_URL}）")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[エラー] Ollama APIへの接続に失敗しました: {e}")
        return None

    print("[INFO] 受信中...")

    response_text = ""

    try:
        for line in response.iter_lines():
            if not line:
                continue

            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[エラー] レスポンス行のパースに失敗しました: {e}")
                print("[詳細] 受信した行（そのまま）:")
                print(line)
                return None

            if "error" in chunk:
                print(f"[エラー] Ollamaからエラーが返されました: {chunk['error']}")
                return None

            piece = chunk.get("response", "")
            response_text += piece
            print(piece, end="", flush=True)

            if chunk.get("done"):
                break
    except requests.exceptions.RequestException as e:
        print(f"\n[エラー] Ollama APIからの受信中に失敗しました: {e}")
        return None

    print()

    json_text = extract_json_text(response_text)

    try:
        question_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print("[エラー] 生成結果のJSONパースに失敗しました")
        print(f"[詳細] {e}")
        print("[LLM出力（そのまま）]")
        print(response_text)
        return None

    question_data = shuffle_choices(question_data)
    if question_data is None:
        print("[エラー] correct_answerがA〜Dのいずれでもないため、選択肢のシャッフルに失敗しました")
        return None

    return question_data


def save_pending(question_data):
    """生成結果を questions/pending/ に保存し、保存先のパスを返す。"""

    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = PENDING_DIR / f"generated_{timestamp}.json"

    # 同一秒に複数生成された場合は連番を付けて衝突を避ける
    n = 2
    while filepath.exists():
        filepath = PENDING_DIR / f"generated_{timestamp}_{n}.json"
        n += 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(question_data, f, ensure_ascii=False, indent=2)

    return filepath


def main():
    count = 1
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"[エラー] 問題数は整数で指定してください: {sys.argv[1]}")
            sys.exit(1)

        if count < 1:
            print(f"[エラー] 問題数は1以上で指定してください: {count}")
            sys.exit(1)

    prompt = load_prompt()

    success_count = 0

    for i in range(1, count + 1):
        print(f"[INFO] {i}/{count} 問目を生成します")

        question_data = generate_one(prompt)
        if question_data is None:
            print(f"[エラー] {i}/{count} 問目の生成に失敗しました")
            continue

        print("[INFO] 生成結果:")
        print(json.dumps(question_data, ensure_ascii=False, indent=2))

        filepath = save_pending(question_data)
        print(f"[INFO] 保存しました: {filepath.relative_to(BASE_DIR)}")

        success_count += 1

    print(f"[INFO] 完了: 成功 {success_count}/{count} 件")

    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
