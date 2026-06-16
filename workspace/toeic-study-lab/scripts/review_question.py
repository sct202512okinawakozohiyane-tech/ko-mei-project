import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "review" / "review_part5.txt"
PENDING_DIR = BASE_DIR / "questions" / "pending"
REVIEWED_DIR = BASE_DIR / "questions" / "reviewed"
LOGS_DIR = BASE_DIR / "logs"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL_NAME = os.environ.get("KOMEI_MODEL", "gemma4:e4b")
REQUEST_TIMEOUT = (10, 600)


def ensure_dirs():
    REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


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
    text = "\n".join(lines).strip()

    # ブロック内にJSONが埋め込まれている場合の抽出
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def save_error_log(filename, raw_response, error_msg):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"review_error_{timestamp}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"source_file: {filename}\n")
        f.write(f"error: {error_msg}\n\n")
        f.write("--- raw response ---\n")
        f.write(raw_response)
    print(f"[エラーログ] 保存しました: {log_path.relative_to(BASE_DIR)}")


def call_ollama(prompt_text):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt_text,
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
    return response_text


def review_one(pending_file, prompt_template):
    print(f"[INFO] レビュー対象: {pending_file.name}")

    with open(pending_file, encoding="utf-8") as f:
        question_data = json.load(f)

    question_json_str = json.dumps(question_data, ensure_ascii=False, indent=2)
    prompt_text = prompt_template.replace("{{QUESTION_JSON}}", question_json_str)

    print(f"[INFO] Ollamaにレビューをリクエストします（model={MODEL_NAME}）")
    raw_response = call_ollama(prompt_text)

    if raw_response is None:
        return None, None

    json_text = extract_json_text(raw_response)

    try:
        review_result = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"[エラー] レビュー結果のJSONパースに失敗しました: {e}")
        save_error_log(pending_file.name, raw_response, str(e))
        return None, None

    # original_file を相対パスで付加
    original_file_rel = str(pending_file.relative_to(BASE_DIR))
    reviewed_data = {"original_file": original_file_rel}
    reviewed_data.update(review_result)

    return reviewed_data, raw_response


def save_reviewed(reviewed_data):
    REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REVIEWED_DIR / f"reviewed_{timestamp}.json"

    n = 2
    while filepath.exists():
        filepath = REVIEWED_DIR / f"reviewed_{timestamp}_{n}.json"
        n += 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(reviewed_data, f, ensure_ascii=False, indent=2)

    return filepath


def get_pending_files(count):
    files = sorted(PENDING_DIR.glob("generated_*.json"))
    if not files:
        print("[INFO] pending/ にレビュー対象ファイルがありません")
        return []
    return files[:count]


def main():
    count = 1
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"[エラー] 件数は整数で指定してください: {sys.argv[1]}")
            sys.exit(1)
        if count < 1:
            print(f"[エラー] 件数は1以上で指定してください: {count}")
            sys.exit(1)

    ensure_dirs()
    prompt_template = load_prompt()
    pending_files = get_pending_files(count)

    if not pending_files:
        sys.exit(0)

    print(f"[INFO] {len(pending_files)} 件をレビューします")

    success_count = 0

    for i, pending_file in enumerate(pending_files, 1):
        print(f"\n[INFO] {i}/{len(pending_files)} 件目")

        reviewed_data, _ = review_one(pending_file, prompt_template)

        if reviewed_data is None:
            print(f"[エラー] {pending_file.name} のレビューに失敗しました")
            continue

        filepath = save_reviewed(reviewed_data)
        status = reviewed_data.get("review_status", "不明")
        print(f"[INFO] 保存しました: {filepath.relative_to(BASE_DIR)} (status={status})")

        success_count += 1

    print(f"\n[INFO] 完了: 成功 {success_count}/{len(pending_files)} 件")

    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
