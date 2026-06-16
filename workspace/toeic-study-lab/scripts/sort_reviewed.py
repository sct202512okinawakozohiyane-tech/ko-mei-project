"""
1次レビュー結果（questions/reviewed/）を元に、pending の問題ファイルを振り分ける。

  approved  → questions/approved/questions.json に追加し、pending・reviewed から削除
  needs_fix → questions/needs_fix/ にコピーし、pending・reviewed から削除
  rejected  → questions/rejected/ にコピーし、pending・reviewed から削除

処理済みの reviewed ファイルは削除するため、再実行しても重複処理にならない。
pending の元ファイルがすでに存在しない場合は「処理済み」としてスキップする。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REVIEWED_DIR = BASE_DIR / "questions" / "reviewed"
APPROVED_FILE = BASE_DIR / "questions" / "approved" / "questions.json"
NEEDS_FIX_DIR = BASE_DIR / "questions" / "needs_fix"
REJECTED_DIR = BASE_DIR / "questions" / "rejected"

QUESTION_FIELDS = {
    "part", "question_text",
    "choice_a", "choice_b", "choice_c", "choice_d",
    "correct_answer", "explanation", "difficulty", "grammar_point",
    "question_translation", "choice_translations", "choice_explanations",
}


def ensure_dirs():
    APPROVED_FILE.parent.mkdir(parents=True, exist_ok=True)
    NEEDS_FIX_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)


def load_approved_questions():
    if not APPROVED_FILE.exists():
        print(f"[INFO] {APPROVED_FILE.name} が存在しないため空リストで開始します")
        return []
    try:
        with open(APPROVED_FILE, encoding="utf-8") as f:
            data = json.load(f)
        print(f"[INFO] 既存の approved 件数: {len(data)}")
        return data
    except json.JSONDecodeError as e:
        print(f"[エラー] {APPROVED_FILE.name} のパースに失敗しました: {e}")
        print(f"[エラー] ファイルが破損している可能性があります。処理を中断します")
        sys.exit(1)


def save_approved_questions(questions):
    """アトミック書き込み: 一時ファイルに書いてからリネームして破損を防ぐ。"""
    tmp_path = APPROVED_FILE.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, APPROVED_FILE)


def is_duplicate(question_text, existing_questions):
    for q in existing_questions:
        if q.get("question_text", "").strip() == question_text.strip():
            return True
    return False


def save_timestamped(data, directory, prefix):
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = directory / f"{prefix}_{timestamp}.json"
    n = 2
    while filepath.exists():
        filepath = directory / f"{prefix}_{timestamp}_{n}.json"
        n += 1
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def load_original_question(reviewed_data):
    original_file_rel = reviewed_data.get("original_file")
    if not original_file_rel:
        return None, None, "no_field"

    original_path = BASE_DIR / original_file_rel
    if not original_path.exists():
        return None, original_path, "not_found"

    with open(original_path, encoding="utf-8") as f:
        data = json.load(f)

    question_data = {k: v for k, v in data.items() if k in QUESTION_FIELDS}
    return question_data, original_path, "ok"


def process_reviewed_file(reviewed_file, approved_questions):
    try:
        with open(reviewed_file, encoding="utf-8") as f:
            reviewed_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [エラー] 読み込み失敗: {e}")
        return "error"

    status = reviewed_data.get("review_status", "")
    print(f"  review_status: {status}")

    question_data, original_path, load_status = load_original_question(reviewed_data)

    if load_status == "no_field":
        print(f"  [エラー] original_file フィールドがありません")
        return "error"

    if load_status == "not_found":
        # pending がすでに存在しない = 前回の sort_reviewed.py で処理済み
        print(f"  [スキップ] pending 元ファイルなし（処理済み）→ reviewed ファイルを削除")
        reviewed_file.unlink()
        return "already_done"

    question_text = question_data.get("question_text", "")

    if status == "approved":
        if is_duplicate(question_text, approved_questions):
            print(f"  [スキップ] 重複のためスキップ: {question_text[:50]}...")
            reviewed_file.unlink()
            return "duplicate"
        approved_questions.append(question_data)
        original_path.unlink()
        reviewed_file.unlink()
        print(f"  [OK] approved/questions.json に追加 → pending・reviewed から削除")
        return "approved"

    elif status == "needs_fix":
        # レビューコメント（issues/suggestions）を question と一緒に保存する
        review_keys = {"review_status", "score", "correct_answer", "issues", "suggestions", "confidence"}
        combined = {k: v for k, v in reviewed_data.items() if k in review_keys}
        combined["question"] = question_data
        filepath = save_timestamped(combined, NEEDS_FIX_DIR, "needs_fix")
        original_path.unlink()
        reviewed_file.unlink()
        print(f"  [OK] 保存: {filepath.relative_to(BASE_DIR)} → pending・reviewed から削除")
        return "needs_fix"

    elif status == "rejected":
        filepath = save_timestamped(question_data, REJECTED_DIR, "rejected")
        original_path.unlink()
        reviewed_file.unlink()
        print(f"  [OK] 保存: {filepath.relative_to(BASE_DIR)} → pending・reviewed から削除")
        return "rejected"

    else:
        print(f"  [警告] 不明な review_status: '{status}' — スキップ")
        return "unknown"


def main():
    ensure_dirs()

    reviewed_files = sorted(REVIEWED_DIR.glob("reviewed_*.json"))

    if not reviewed_files:
        print("[INFO] reviewed/ に対象ファイルがありません")
        sys.exit(0)

    print(f"[INFO] {len(reviewed_files)} 件を振り分けます")

    approved_questions = load_approved_questions()

    counts = {"approved": 0, "needs_fix": 0, "rejected": 0,
              "duplicate": 0, "already_done": 0, "error": 0, "unknown": 0}

    for i, reviewed_file in enumerate(reviewed_files, 1):
        print(f"\n[INFO] {i}/{len(reviewed_files)} 件目: {reviewed_file.name}")
        result = process_reviewed_file(reviewed_file, approved_questions)
        counts[result] = counts.get(result, 0) + 1

    if counts["approved"] > 0:
        save_approved_questions(approved_questions)
        print(f"\n[INFO] approved/questions.json を更新しました（合計 {len(approved_questions)} 件）")

    print(f"\n[INFO] 振り分け完了:")
    print(f"  approved    : {counts['approved']} 件")
    print(f"  needs_fix   : {counts['needs_fix']} 件")
    print(f"  rejected    : {counts['rejected']} 件")
    print(f"  duplicate   : {counts['duplicate']} 件（スキップ）")
    print(f"  already_done: {counts['already_done']} 件（処理済み・reviewed 削除）")
    print(f"  error       : {counts['error']} 件")


if __name__ == "__main__":
    main()
