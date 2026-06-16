import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REREVIEWED_DIR = BASE_DIR / "questions" / "rereviewed"
REWRITTEN_DIR = BASE_DIR / "questions" / "rewritten"
APPROVED_FILE = BASE_DIR / "questions" / "approved" / "questions.json"
REJECTED_DIR = BASE_DIR / "questions" / "rejected"
NEEDS_FIX_DIR = BASE_DIR / "questions" / "needs_fix"
LOGS_DIR = BASE_DIR / "logs"

# 問題データとして保存するフィールド（メタ情報は除外）
QUESTION_FIELDS = {
    "part", "question_text",
    "choice_a", "choice_b", "choice_c", "choice_d",
    "correct_answer", "explanation", "difficulty", "grammar_point",
    "question_translation", "choice_translations", "choice_explanations",
}


def ensure_dirs():
    APPROVED_FILE.parent.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    NEEDS_FIX_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_approved_questions():
    if not APPROVED_FILE.exists():
        return []
    with open(APPROVED_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_approved_questions(questions):
    with open(APPROVED_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def is_duplicate(question_text, existing_questions):
    for q in existing_questions:
        if q.get("question_text", "").strip() == question_text.strip():
            return True
    return False


def extract_question_data(rewritten_data):
    """rewritten ファイルから問題データのみ抽出する（メタフィールドを除く）。"""
    return {k: v for k, v in rewritten_data.items() if k in QUESTION_FIELDS}


def load_rewritten_question(rereviewed_data, rereviewed_file):
    source_rewritten_rel = rereviewed_data.get("source_rewritten")
    if not source_rewritten_rel:
        print(f"[エラー] source_rewritten フィールドがありません: {rereviewed_file.name}")
        return None

    rewritten_path = BASE_DIR / source_rewritten_rel
    if not rewritten_path.exists():
        print(f"[エラー] 修正版ファイルが見つかりません: {rewritten_path}")
        return None

    with open(rewritten_path, encoding="utf-8") as f:
        return json.load(f)


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


def process_rereviewed_file(rereviewed_file, approved_questions):
    try:
        with open(rereviewed_file, encoding="utf-8") as f:
            rereviewed_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[エラー] {rereviewed_file.name} の読み込みに失敗しました: {e}")
        return "error"

    status = rereviewed_data.get("review_status", "")
    print(f"  review_status: {status}")

    if status == "approved":
        rewritten_data = load_rewritten_question(rereviewed_data, rereviewed_file)
        if rewritten_data is None:
            return "error"

        question_data = extract_question_data(rewritten_data)
        question_text = question_data.get("question_text", "")

        if not question_text:
            print(f"[エラー] question_text が空です: {rereviewed_file.name}")
            return "error"

        if is_duplicate(question_text, approved_questions):
            print(f"[スキップ] 重複のためスキップします: {question_text[:50]}...")
            return "duplicate"

        approved_questions.append(question_data)
        print(f"[OK] approved/questions.json に追加しました")
        return "approved"

    elif status == "rejected":
        filepath = save_timestamped(rereviewed_data, REJECTED_DIR, "rejected")
        print(f"[OK] 保存しました: {filepath.relative_to(BASE_DIR)}")
        return "rejected"

    elif status == "needs_fix":
        # needs_fix の場合は修正版問題を needs_fix/ に保存して次のサイクルへ
        rewritten_data = load_rewritten_question(rereviewed_data, rereviewed_file)
        if rewritten_data is None:
            # rewritten ファイルがない場合は rereviewed データをそのまま保存
            filepath = save_timestamped(rereviewed_data, NEEDS_FIX_DIR, "needs_fix")
        else:
            question_data = extract_question_data(rewritten_data)
            filepath = save_timestamped(question_data, NEEDS_FIX_DIR, "needs_fix")
        print(f"[OK] 保存しました: {filepath.relative_to(BASE_DIR)}")
        return "needs_fix"

    else:
        print(f"[警告] 不明な review_status: '{status}' — スキップします")
        return "unknown"


def main():
    ensure_dirs()

    rereviewed_files = sorted(REREVIEWED_DIR.glob("rereviewed_*.json"))

    if not rereviewed_files:
        print("[INFO] rereviewed/ に対象ファイルがありません")
        sys.exit(0)

    print(f"[INFO] {len(rereviewed_files)} 件を振り分けます")

    approved_questions = load_approved_questions()
    print(f"[INFO] 既存の approved 件数: {len(approved_questions)}")

    counts = {"approved": 0, "rejected": 0, "needs_fix": 0, "duplicate": 0, "error": 0, "unknown": 0}

    for i, rereviewed_file in enumerate(rereviewed_files, 1):
        print(f"\n[INFO] {i}/{len(rereviewed_files)} 件目: {rereviewed_file.name}")
        result = process_rereviewed_file(rereviewed_file, approved_questions)
        counts[result] = counts.get(result, 0) + 1

    # approved/questions.json への書き込みは最後に一括して行う
    if counts["approved"] > 0:
        save_approved_questions(approved_questions)
        print(f"\n[INFO] approved/questions.json を更新しました（合計 {len(approved_questions)} 件）")

    print(f"\n[INFO] 振り分け完了:")
    print(f"  approved  : {counts['approved']} 件")
    print(f"  rejected  : {counts['rejected']} 件")
    print(f"  needs_fix : {counts['needs_fix']} 件")
    print(f"  duplicate : {counts['duplicate']} 件（スキップ）")
    print(f"  error     : {counts['error']} 件")
    if counts.get("unknown", 0):
        print(f"  unknown   : {counts['unknown']} 件")


if __name__ == "__main__":
    main()
