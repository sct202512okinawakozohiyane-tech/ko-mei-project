#!/usr/bin/env bash
set -euo pipefail

PENDING_DIR="${1:-questions/pending}"
OUT_DIR="${2:-feedback/reviews}"

mkdir -p "$OUT_DIR"

if [ ! -d "$PENDING_DIR" ]; then
  echo "[ERROR] pending dir not found: $PENDING_DIR"
  exit 1
fi

count=0

for qfile in "$PENDING_DIR"/*.json; do
  [ -e "$qfile" ] || {
    echo "[INFO] JSONファイルがありません: $PENDING_DIR"
    exit 0
  }

  base="$(basename "$qfile" .json)"
  outfile="$OUT_DIR/${base}.review.json"

  echo "[INFO] reviewing: $qfile"

  ./scripts/review_question.sh "$qfile" > "$outfile"

  echo "[OK] saved: $outfile"
  count=$((count + 1))
done

echo "[DONE] reviewed $count file(s)"
