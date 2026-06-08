#!/bin/bash
set -euo pipefail

SRC_DIR="questions/rejected"
OUT_DIR="questions/pending"

mkdir -p "$OUT_DIR"

for q in "$SRC_DIR"/*.json; do
  [[ "$q" == *.review.json ]] && continue

  review="${q%.json}.review.json"
  base=$(basename "$q" .json)

  if [ ! -f "$review" ]; then
    echo "⚠ review not found: $base"
    continue
  fi

  out="$OUT_DIR/${base}.fix1.json"

  echo "🔧 fixing: $base"
  ./scripts/fix_question.sh "$q" "$review" \
  | sed -n '/^{/,/^}/p' > "$out"

  if jq empty "$out" >/dev/null 2>&1; then
    echo "✅ fixed -> $out"
  else
    echo "❌ invalid json: $out"
  fi
done
