#!/usr/bin/env bash
set -euo pipefail

MODEL="${KOMEI_MODEL:-gemma4:e4b}"
OLLAMA_URL="${OLLAMA_URL:-http://ollama:11434/api/generate}"

PROMPT="$(cat)"

jq -n \
  --arg model "$MODEL" \
  --arg prompt "$PROMPT" \
  '{
    model: $model,
    prompt: $prompt,
    stream: false
  }' \
| curl -s "$OLLAMA_URL" \
  -H "Content-Type: application/json" \
  -d @- \
| jq -r '.response'
