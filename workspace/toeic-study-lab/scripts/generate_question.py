import json
import os
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "questions" / "generate_part5.txt"

# コンテナ内（ko-meiコンテナ）からの実行を想定したデフォルト値。
# コンテナ外でローカルのOllamaを使う場合は、環境変数で上書きする。
#   OLLAMA_URL=http://localhost:11434/api/generate python scripts/generate_question.py
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL_NAME = os.environ.get("KOMEI_MODEL", "gemma4:e4b")

REQUEST_TIMEOUT = 300


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


def main():
    prompt = load_prompt()

    print(f"[INFO] Ollamaに問題生成をリクエストします（model={MODEL_NAME}, url={OLLAMA_URL}）")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[エラー] Ollama APIへの接続に失敗しました: {e}")
        sys.exit(1)

    try:
        api_data = response.json()
    except json.JSONDecodeError as e:
        print(f"[エラー] APIレスポンスのパースに失敗しました: {e}")
        print("[詳細] レスポンス本文（そのまま）:")
        print(response.text)
        sys.exit(1)

    if "response" not in api_data:
        print("[エラー] APIレスポンスに 'response' フィールドがありません")
        print(json.dumps(api_data, ensure_ascii=False, indent=2))
        sys.exit(1)

    response_text = api_data["response"]
    json_text = extract_json_text(response_text)

    try:
        question_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print("[エラー] 生成結果のJSONパースに失敗しました")
        print(f"[詳細] {e}")
        print("[LLM出力（そのまま）]")
        print(response_text)
        sys.exit(1)

    print("[INFO] 生成結果:")
    print(json.dumps(question_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
