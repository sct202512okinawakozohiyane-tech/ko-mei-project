import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "rewrite" / "rewrite_part5.txt"
NEEDS_FIX_DIR = BASE_DIR / "questions" / "needs_fix"
REWRITTEN_DIR = BASE_DIR / "questions" / "rewritten"
LOGS_DIR = BASE_DIR / "logs"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL_NAME = os.environ.get("KOMEI_MODEL", "gemma4:e4b")
REQUEST_TIMEOUT = (10, 600)


def ensure_dirs():
    REWRITTEN_DIR.mkdir(parents=True, exist_ok=True)
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
    log_path = LOGS_DIR / f"rewrite_error_{timestamp}.log"
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


def get_needs_fix_files():
    files = sorted(NEEDS_FIX_DIR.glob("needs_fix_*.json"))
    result = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            result.append((f, data))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[警告] {f.name} の読み込みに失敗しました: {e}")
    return result


def split_needs_fix_data(data):
    """needs_fix ファイルから question データと review データを分離して返す。

    sort_reviewed.py で保存した新形式（question キーあり）と、
    旧形式（question フィールドのみのフラット構造）の両方に対応する。
    """
    if "question" in data:
        question_data = data["question"]
        review_data = {k: v for k, v in data.items() if k != "question"}
    else:
        question_data = data
        review_data = {}
    return question_data, review_data


def rewrite_one(needs_fix_file, file_data, prompt_template):
    print(f"[INFO] 修正対象: {needs_fix_file.name}")

    question_data, review_data = split_needs_fix_data(file_data)

    original_json_str = json.dumps(question_data, ensure_ascii=False, indent=2)
    review_json_str = json.dumps(review_data, ensure_ascii=False, indent=2) if review_data else "{}"

    if not review_data:
        print(f"[警告] レビューコメントなし（旧形式）— 問題データのみで修正を試みます")

    prompt_text = prompt_template.replace("{{ORIGINAL_QUESTION}}", original_json_str)
    prompt_text = prompt_text.replace("{{REVIEW_RESULT}}", review_json_str)

    print(f"[INFO] Ollamaに修正をリクエストします（model={MODEL_NAME}）")
    raw_response = call_ollama(prompt_text)

    if raw_response is None:
        return None

    json_text = extract_json_text(raw_response)

    try:
        rewritten_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"[エラー] 修正結果のJSONパースに失敗しました: {e}")
        save_error_log(needs_fix_file.name, raw_response, str(e))
        return None

    rewritten_data["source_needs_fix"] = str(needs_fix_file.relative_to(BASE_DIR))

    return rewritten_data


def save_rewritten(rewritten_data):
    REWRITTEN_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REWRITTEN_DIR / f"rewritten_{timestamp}.json"

    n = 2
    while filepath.exists():
        filepath = REWRITTEN_DIR / f"rewritten_{timestamp}_{n}.json"
        n += 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(rewritten_data, f, ensure_ascii=False, indent=2)

    return filepath


def main():
    ensure_dirs()
    prompt_template = load_prompt()

    needs_fix_files = get_needs_fix_files()

    if not needs_fix_files:
        print("[INFO] needs_fix/ に対象ファイルがありません")
        sys.exit(0)

    print(f"[INFO] needs_fix: {len(needs_fix_files)} 件を修正します")

    success_count = 0

    for i, (needs_fix_file, file_data) in enumerate(needs_fix_files, 1):
        print(f"\n[INFO] {i}/{len(needs_fix_files)} 件目")

        rewritten_data = rewrite_one(needs_fix_file, file_data, prompt_template)

        if rewritten_data is None:
            print(f"[エラー] {needs_fix_file.name} の修正に失敗しました")
            continue

        filepath = save_rewritten(rewritten_data)
        print(f"[INFO] 保存しました: {filepath.relative_to(BASE_DIR)}")

        success_count += 1

    print(f"\n[INFO] 完了: 成功 {success_count}/{len(needs_fix_files)} 件")

    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
