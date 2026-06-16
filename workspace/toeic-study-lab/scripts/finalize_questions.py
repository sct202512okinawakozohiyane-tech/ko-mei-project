import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REREVIEWED_DIR = BASE_DIR / "questions" / "rereviewed"
REWRITTEN_DIR = BASE_DIR / "questions" / "rewritten"
NEEDS_FIX_DIR = BASE_DIR / "questions" / "needs_fix"
APPROVED_FILE = BASE_DIR / "questions" / "approved" / "questions.json"
REJECTED_DIR = BASE_DIR / "questions" / "rejected"

QUESTION_FIELDS = {
    "part", "question_text",
    "choice_a", "choice_b", "choice_c", "choice_d",
    "correct_answer", "explanation", "difficulty",
    "grammar_category", "grammar_point",
    "question_translation", "choice_translations", "choice_explanations",
}


def ensure_dirs():
    APPROVED_FILE.parent.mkdir(parents=True, exist_ok=True)
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


def extract_question_data(data):
    return {k: v for k, v in data.items() if k in QUESTION_FIELDS}


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


def load_rewritten(rereviewed_data):
    """rereviewed データから source_rewritten を辿って rewritten データを読み込む。"""
    rel = rereviewed_data.get("source_rewritten")
    if not rel:
        return None, None
    path = BASE_DIR / rel
    if not path.exists():
        return None, path
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def cleanup_sources(rereviewed_file, rereviewed_data):
    """rereviewed → rewritten → needs_fix の順にファイルを削除する。"""
    rewritten_data, rewritten_path = load_rewritten(rereviewed_data)

    # needs_fix ファイルの削除（rewritten ファイルが持つ参照をたどる）
    if rewritten_data:
        needs_fix_rel = rewritten_data.get("source_needs_fix")
        if needs_fix_rel:
            needs_fix_path = BASE_DIR / needs_fix_rel
            if needs_fix_path.exists():
                needs_fix_path.unlink()
                print(f"  [削除] {needs_fix_rel}")

    # rewritten ファイルの削除
    if rewritten_path and rewritten_path.exists():
        rewritten_path.unlink()
        print(f"  [削除] {rewritten_path.relative_to(BASE_DIR)}")

    # rereviewed ファイルの削除
    if rereviewed_file.exists():
        rereviewed_file.unlink()
        print(f"  [削除] {rereviewed_file.relative_to(BASE_DIR)}")


def process_rereviewed_file(rereviewed_file, approved_questions):
    try:
        with open(rereviewed_file, encoding="utf-8") as f:
            rereviewed_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [エラー] 読み込み失敗: {e}")
        return "error"

    status = rereviewed_data.get("review_status", "")
    print(f"  review_status: {status}")

    if status == "approved":
        rewritten_data, _ = load_rewritten(rereviewed_data)
        if rewritten_data is None:
            print(f"  [エラー] rewritten ファイルが見つかりません")
            return "error"

        question_data = extract_question_data(rewritten_data)
        question_text = question_data.get("question_text", "")

        if not question_text:
            print(f"  [エラー] question_text が空です")
            return "error"

        if is_duplicate(question_text, approved_questions):
            print(f"  [スキップ] 重複: {question_text[:50]}...")
            cleanup_sources(rereviewed_file, rereviewed_data)
            return "duplicate"

        approved_questions.append(question_data)
        cleanup_sources(rereviewed_file, rereviewed_data)
        print(f"  [OK] approved/questions.json に追加")
        return "approved"

    elif status in ("rejected", "needs_fix"):
        # needs_fix は3度目のレビューを行わずリジェクト扱い
        if status == "needs_fix":
            print(f"  [INFO] needs_fix → rejected として処理します")

        rewritten_data, _ = load_rewritten(rereviewed_data)
        if rewritten_data:
            question_data = extract_question_data(rewritten_data)
        else:
            question_data = {}

        rejected_data = {
            "review_status": "rejected",
            "original_review_status": status,
            "rereviewed_file": rereviewed_file.name,
            "question": question_data,
            "issues": rereviewed_data.get("issues", []),
            "suggestions": rereviewed_data.get("suggestions", []),
        }
        filepath = save_timestamped(rejected_data, REJECTED_DIR, "rejected")
        cleanup_sources(rereviewed_file, rereviewed_data)
        print(f"  [OK] 保存: {filepath.relative_to(BASE_DIR)}")
        return "rejected"

    else:
        print(f"  [警告] 不明な review_status: '{status}' — スキップ")
        return "unknown"


def main():
    ensure_dirs()

    rereviewed_files = sorted(REREVIEWED_DIR.glob("rereviewed_*.json"))

    if not rereviewed_files:
        print("[INFO] rereviewed/ に対象ファイルがありません")
        sys.exit(0)

    print(f"[INFO] {len(rereviewed_files)} 件を振り分けます")

    approved_questions = load_approved_questions()

    counts = {"approved": 0, "rejected": 0, "duplicate": 0, "error": 0, "unknown": 0}

    for i, rereviewed_file in enumerate(rereviewed_files, 1):
        print(f"\n[INFO] {i}/{len(rereviewed_files)} 件目: {rereviewed_file.name}")
        result = process_rereviewed_file(rereviewed_file, approved_questions)
        counts[result] = counts.get(result, 0) + 1

    if counts["approved"] > 0:
        save_approved_questions(approved_questions)
        print(f"\n[INFO] approved/questions.json を更新しました（合計 {len(approved_questions)} 件）")

    print(f"\n[INFO] 振り分け完了:")
    print(f"  approved  : {counts['approved']} 件")
    print(f"  rejected  : {counts['rejected']} 件（needs_fix のリジェクト含む）")
    print(f"  duplicate : {counts['duplicate']} 件（スキップ）")
    print(f"  error     : {counts['error']} 件")


if __name__ == "__main__":
    main()
