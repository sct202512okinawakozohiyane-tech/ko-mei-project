import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "review" / "review_part5.txt"
REWRITTEN_DIR = BASE_DIR / "questions" / "rewritten"
REREVIEWED_DIR = BASE_DIR / "questions" / "rereviewed"
LOGS_DIR = BASE_DIR / "logs"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL_NAME = os.environ.get("KOMEI_MODEL", "gemma4:e4b")
REQUEST_TIMEOUT = (10, 600)


def ensure_dirs():
    REREVIEWED_DIR.mkdir(parents=True, exist_ok=True)
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

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def save_error_log(filename, raw_response, error_msg):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"rereview_error_{timestamp}.log"
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


def get_rewritten_question(rewritten_data):
    # source_reviewed / original_file などのメタフィールドを除いた問題データを返す
    meta_keys = {"source_reviewed", "original_file", "brief_note"}
    return {k: v for k, v in rewritten_data.items() if k not in meta_keys}


def rereview_one(rewritten_file, rewritten_data, prompt_template):
    print(f"[INFO] 再レビュー対象: {rewritten_file.name}")

    question_data = get_rewritten_question(rewritten_data)
    question_json_str = json.dumps(question_data, ensure_ascii=False, indent=2)
    prompt_text = prompt_template.replace("{{QUESTION_JSON}}", question_json_str)

    print(f"[INFO] Ollamaに再レビューをリクエストします（model={MODEL_NAME}）")
    raw_response = call_ollama(prompt_text)

    if raw_response is None:
        return None

    json_text = extract_json_text(raw_response)

    try:
        review_result = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"[エラー] 再レビュー結果のJSONパースに失敗しました: {e}")
        save_error_log(rewritten_file.name, raw_response, str(e))
        return None

    rereviewed_data = {
        "source_rewritten": str(rewritten_file.relative_to(BASE_DIR)),
        "original_file": rewritten_data.get("original_file", ""),
    }
    rereviewed_data.update(review_result)

    return rereviewed_data


def save_rereviewed(rereviewed_data):
    REREVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REREVIEWED_DIR / f"rereviewed_{timestamp}.json"

    n = 2
    while filepath.exists():
        filepath = REREVIEWED_DIR / f"rereviewed_{timestamp}_{n}.json"
        n += 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(rereviewed_data, f, ensure_ascii=False, indent=2)

    return filepath


def main():
    ensure_dirs()
    prompt_template = load_prompt()

    rewritten_files = sorted(REWRITTEN_DIR.glob("rewritten_*.json"))

    if not rewritten_files:
        print("[INFO] rewritten/ に対象ファイルがありません")
        sys.exit(0)

    print(f"[INFO] {len(rewritten_files)} 件を再レビューします")

    success_count = 0

    for i, rewritten_file in enumerate(rewritten_files, 1):
        print(f"\n[INFO] {i}/{len(rewritten_files)} 件目")

        try:
            with open(rewritten_file, encoding="utf-8") as f:
                rewritten_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[エラー] {rewritten_file.name} の読み込みに失敗しました: {e}")
            continue

        rereviewed_data = rereview_one(rewritten_file, rewritten_data, prompt_template)

        if rereviewed_data is None:
            print(f"[エラー] {rewritten_file.name} の再レビューに失敗しました")
            continue

        filepath = save_rereviewed(rereviewed_data)
        status = rereviewed_data.get("review_status", "不明")
        print(f"[INFO] 保存しました: {filepath.relative_to(BASE_DIR)} (status={status})")

        success_count += 1

    print(f"\n[INFO] 完了: 成功 {success_count}/{len(rewritten_files)} 件")

    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
