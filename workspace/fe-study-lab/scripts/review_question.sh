#!/usr/bin/env bash
set -euo pipefail

QUESTION_FILE="${1:-}"

if [ -z "$QUESTION_FILE" ]; then
  echo "Usage: $0 questions/approved/FE-ALG-xxxx.json"
  exit 1
fi

if [ ! -f "$QUESTION_FILE" ]; then
  echo "File not found: $QUESTION_FILE"
  exit 1
fi

PROMPT_FILE="komei_tasks/prompts/review_algorithm_question.txt"

{
  cat "$PROMPT_FILE"
  echo
  echo "【レビュー対象JSON】"
  cat "$QUESTION_FILE"
} | ./scripts/ask_komei_raw.sh
