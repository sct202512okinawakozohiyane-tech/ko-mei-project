"""
DB内の問題数をカテゴリ別に集計して表示する。

使用例:
    python scripts/question_distribution.py
    python scripts/question_distribution.py --threshold 5   # 不足判定の閾値を変更（デフォルト: 5）
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from categories import CATEGORIES, LEVEL_NAMES

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "toeic.db"

DEFAULT_THRESHOLD = 5


def fetch_distribution(cur):
    """grammar_category ごとの件数を {category: count} で返す。"""
    cur.execute("""
        SELECT grammar_category, COUNT(*) AS cnt
        FROM questions
        GROUP BY grammar_category
    """)
    rows = cur.fetchall()
    return {(row[0] or "uncategorized"): row[1] for row in rows}


def fetch_total(cur):
    cur.execute("SELECT COUNT(*) FROM questions")
    return cur.fetchone()[0]


def print_distribution(dist, total, threshold):
    width = 20

    print()
    print("=" * 36)
    print("  TOEIC Question Distribution")
    print("=" * 36)

    current_level = None
    for cat_key, cat in CATEGORIES.items():
        if cat["level"] != current_level:
            current_level = cat["level"]
            print(f"\n  --- Level {current_level}: {LEVEL_NAMES[current_level]} ---")

        count = dist.get(cat_key, 0)
        bar = "#" * min(count, 30)
        label = f"{cat_key} ({cat['label']})"
        print(f"  {label:<{width}} : {count:>4}  {bar}")

    # 未カテゴリ（旧データ）
    uncategorized = dist.get("uncategorized", 0)
    if uncategorized:
        print(f"\n  {'uncategorized':<{width}} : {uncategorized:>4}  （旧データ）")

    print()
    print(f"  {'Total':<{width}} : {total:>4}")
    print("=" * 36)

    # 不足カテゴリの警告
    short = {
        cat_key: dist.get(cat_key, 0)
        for cat_key in CATEGORIES
        if dist.get(cat_key, 0) < threshold
    }

    if short:
        print(f"\n[WARNING] 件数が {threshold} 件未満のカテゴリ:")
        for cat_key, count in sorted(short.items(), key=lambda x: x[1]):
            cat = CATEGORIES[cat_key]
            print(f"  {cat_key} ({cat['label']}) : {count}")
    else:
        print(f"\n[OK] 全カテゴリが {threshold} 件以上あります")

    print()


def main():
    threshold = DEFAULT_THRESHOLD
    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        try:
            threshold = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print(f"[エラー] --threshold の値が不正です")
            sys.exit(1)

    if not DB_PATH.exists():
        print(f"[エラー] DBが見つかりません: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    dist = fetch_distribution(cur)
    total = fetch_total(cur)

    conn.close()

    print_distribution(dist, total, threshold)


if __name__ == "__main__":
    main()
