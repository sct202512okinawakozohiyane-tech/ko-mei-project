#!/bin/bash
set -e

PROJECT_ROOT=./fe-study-lab
PROMPT_FILE="$PROJECT_ROOT/komei_tasks/prompts/generate_algorithm_question.txt"
THEMES_FILE="$PROJECT_ROOT/komei_tasks/prompts/algorithm_themes.txt"
DIFFICULTIES_FILE="$PROJECT_ROOT/komei_tasks/prompts/algorithm_difficulties.txt"
PENDING_DIR="$PROJECT_ROOT/questions/pending"
MODEL="gemma4:e4b"
API_URL="http://ollama:11434/api/generate"

# 一時ファイルの後片付け
PAYLOAD_FILE=""
RESPONSE_FILE=""
cleanup() {
  [ -n "$PAYLOAD_FILE" ] && rm -f "$PAYLOAD_FILE"
  [ -n "$RESPONSE_FILE" ] && rm -f "$RESPONSE_FILE"
}
trap cleanup EXIT

# 1. プロジェクトルートに移動
cd "$PROJECT_ROOT"

# 2. プロンプトファイルとテーマ一覧ファイルの確認
if [ ! -f "$PROMPT_FILE" ]; then
  echo "[エラー] プロンプトファイルが見つかりません: $PROMPT_FILE"
  exit 1
fi

if [ ! -f "$THEMES_FILE" ]; then
  echo "[エラー] テーマ一覧ファイルが見つかりません: $THEMES_FILE"
  exit 1
fi

if [ ! -f "$DIFFICULTIES_FILE" ]; then
  echo "[エラー] 難易度一覧ファイルが見つかりません: $DIFFICULTIES_FILE"
  exit 1
fi

echo "[INFO] プロンプトファイルを読み込みました"

# 3. テーマを選択し、APIリクエストのJSONペイロードをPythonで作成
PAYLOAD_FILE=$(mktemp)
python3 - <<PYEOF
import json, random

# テーマ一覧を読み込み、空行を除外してランダムに1つ選ぶ
with open("$THEMES_FILE", encoding="utf-8") as f:
    themes = [line.strip() for line in f if line.strip()]

if not themes:
    print("[エラー] テーマ一覧が空です")
    import sys; sys.exit(1)

theme = random.choice(themes)
print(f"[INFO] 今回のテーマ: {theme}")

# 難易度一覧を読み込み、空行を除外してランダムに1つ選ぶ
with open("$DIFFICULTIES_FILE", encoding="utf-8") as f:
    difficulties = [line.strip() for line in f if line.strip()]

if not difficulties:
    print("[エラー] 難易度一覧が空です")
    import sys; sys.exit(1)

difficulty = random.choice(difficulties)
print(f"[INFO] 今回の難易度: {difficulty}")

# プロンプトを読み込み、{{THEME}} と {{DIFFICULTY}} を置換する
with open("$PROMPT_FILE", encoding="utf-8") as f:
    prompt = f.read()

prompt = prompt.replace("{{THEME}}", theme)
prompt = prompt.replace("{{DIFFICULTY}}", difficulty)

payload = {"model": "$MODEL", "prompt": prompt, "stream": False}

with open("$PAYLOAD_FILE", "w", encoding="utf-8") as out:
    out.write(json.dumps(payload))
PYEOF

# 4. curl で Ollama API にリクエスト
echo "[INFO] Ollama API にリクエスト中..."
RESPONSE_FILE=$(mktemp)
HTTP_STATUS=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" \
  -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "@$PAYLOAD_FILE")

if [ "$HTTP_STATUS" != "200" ]; then
  echo "[エラー] APIリクエストが失敗しました（HTTPステータス: $HTTP_STATUS）"
  exit 1
fi

echo "[INFO] APIレスポンスを受信しました"

# 5〜9. レスポンスを解析して問題JSONを保存
python3 - "$RESPONSE_FILE" "$PENDING_DIR" <<'PYEOF'
import sys, json, os
from datetime import datetime

response_file = sys.argv[1]
pending_dir   = sys.argv[2]

# questions ディレクトリ（pending の親）から approved/rejected のパスを導出
questions_dir = os.path.dirname(pending_dir)
approved_dir  = os.path.join(questions_dir, "approved")
rejected_dir  = os.path.join(questions_dir, "rejected")

# APIレスポンス全体を読み込む
with open(response_file, encoding="utf-8") as f:
    raw = f.read()

# APIレスポンスJSON から response フィールドを取得
try:
    api_data = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"[エラー] APIレスポンスのパースに失敗しました: {e}")
    sys.exit(1)

if "response" not in api_data:
    print("[エラー] APIレスポンスに 'response' フィールドがありません")
    sys.exit(1)

response_text = api_data["response"].strip()

# ```json や ``` が含まれていたら除去（行単位で処理）
lines = response_text.splitlines()
if lines and lines[0].strip().startswith("```"):
    lines = lines[1:]
if lines and lines[-1].strip() == "```":
    lines = lines[:-1]
response_text = "\n".join(lines).strip()

# 取り出した内容が正しいJSONか検証
try:
    question_data = json.loads(response_text)
except json.JSONDecodeError as e:
    print(f"[エラー] 生成されたJSONが不正です: {e}")
    print("[詳細] 受信したテキスト（先頭500文字）:")
    print(response_text[:500])
    sys.exit(1)

# 孔明が出力した id は信用せず、タイムスタンプベースの新 ID を生成する
base_id = datetime.now().strftime("FE-ALG-%Y%m%d-%H%M%S")

# pending / approved / rejected すべてで衝突しないファイル名を探す
def exists_in_any(name):
    for d in [pending_dir, approved_dir, rejected_dir]:
        if os.path.exists(os.path.join(d, name)):
            return True
    return False

filename = f"{base_id}.json"
if exists_in_any(filename):
    # 衝突した場合は -01, -02, ... と連番を付ける
    for nn in range(1, 100):
        candidate = f"{base_id}-{nn:02d}.json"
        if not exists_in_any(candidate):
            filename = candidate
            break
    print(f"[INFO] 同名ファイルが存在するため、連番を付けて保存します")

# ファイル名（拡張子なし）を新 ID として question_data に上書きする
new_id = filename[:-5]
question_data["id"] = new_id

# JSONファイルとして保存
filepath = os.path.join(pending_dir, filename)
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(question_data, f, ensure_ascii=False, indent=2)

print(f"[完了] 問題を保存しました: questions/pending/{filename}")
PYEOF
