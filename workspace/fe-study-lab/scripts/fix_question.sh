#!/bin/bash
set -euo pipefail

QUESTION_FILE="${1:-}"
REVIEW_FILE="${2:-}"

if [ -z "$QUESTION_FILE" ] || [ -z "$REVIEW_FILE" ]; then
  echo "Usage: $0 question.json review.json" >&2
  exit 1
fi

PROMPT_FILE="komei_tasks/prompts/fix_algorithm_question.txt"

QUESTION_JSON=$(cat "$QUESTION_FILE")
REVIEW_JSON=$(cat "$REVIEW_FILE")

PROMPT=$(cat "$PROMPT_FILE")
PROMPT="${PROMPT//\{\{QUESTION_JSON\}\}/$QUESTION_JSON}"
PROMPT="${PROMPT//\{\{REVIEW_JSON\}\}/$REVIEW_JSON}"

echo "$PROMPT" | ./scripts/ask_komei_raw.sh
