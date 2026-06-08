import json
import sqlite3
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from flask import Flask, render_template, request, Response, stream_with_context
from gtts import gTTS
import io
from pathlib import Path

app = Flask(__name__)
OLLAMA_URL = "http://ollama:11434/api/chat"
ALLOWED_MODELS = {"gemma4:e4b", "gemma3:4b", "gemma3:1b", "gemma3:270m"}
AUDIO_DIR = Path("/workspace/audio")
AUDIO_DIR.mkdir(exist_ok=True)

DB_PATH = Path("/workspace/chat_history.db")
MAX_CONVERSATIONS = 20


@contextmanager
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                model TEXT,
                messages TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


init_db()


def prune_conversations(conn):
    conn.execute("""
        DELETE FROM conversations WHERE id NOT IN (
            SELECT id FROM conversations ORDER BY updated_at DESC LIMIT ?
        )
    """, (MAX_CONVERSATIONS,))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    messages = data.get("messages") or []
    image_b64 = data.get("image")
    file_text = (data.get("file_text") or "").strip()
    file_name = (data.get("file_name") or "ファイル").strip()
    model = data.get("model") if data.get("model") in ALLOWED_MODELS else "gemma4:e4b"
    think = bool(data.get("think", False))

    if not messages and not image_b64 and not file_text:
        return Response("data: [DONE]\n\n", mimetype="text/event-stream")

    # Enrich the last user message with file attachment and/or image
    ollama_messages = []
    for i, msg in enumerate(messages):
        if i == len(messages) - 1 and msg.get("role") == "user":
            content = msg.get("content", "")
            if file_text:
                content = f"[添付ファイル: {file_name}]\n---\n{file_text}\n---\n\n{content}"
            entry = {"role": "user", "content": content}
            if image_b64:
                entry["images"] = [image_b64]
            ollama_messages.append(entry)
        else:
            ollama_messages.append(msg)

    payload = {"model": model, "messages": ollama_messages, "stream": True, "think": think}

    def generate():
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300000) as resp:
                for line in resp:
                    line = line.strip()
                    if not line:
                        continue
                    chunk = json.loads(line)
                    thinking = chunk.get("message", {}).get("thinking", "")
                    token = chunk.get("message", {}).get("content", "")
                    if thinking:
                        yield f"data: {json.dumps({'thinking': thinking})}\n\n"
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                    if chunk.get("done"):
                        break
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (MAX_CONVERSATIONS,),
        ).fetchall()
    return {"conversations": [dict(row) for row in rows]}


@app.route("/api/conversations/<int:conv_id>", methods=["GET"])
def get_conversation(conv_id):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id, title, model, messages FROM conversations WHERE id = ?",
            (conv_id,),
        ).fetchone()
    if not row:
        return {"error": "not found"}, 404
    return {
        "id": row["id"],
        "title": row["title"],
        "model": row["model"],
        "messages": json.loads(row["messages"]),
    }


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    data = request.get_json() or {}
    title = (data.get("title") or "新しいチャット").strip()[:60]
    messages = data.get("messages") or []
    model = data.get("model", "")
    now = datetime.now(timezone.utc).isoformat()
    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title, model, messages, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, model, json.dumps(messages, ensure_ascii=False), now, now),
        )
        conv_id = cur.lastrowid
        prune_conversations(conn)
    return {"id": conv_id}


@app.route("/api/conversations/<int:conv_id>", methods=["PUT"])
def update_conversation(conv_id):
    data = request.get_json() or {}
    messages = data.get("messages") or []
    model = data.get("model", "")
    now = datetime.now(timezone.utc).isoformat()
    with db_conn() as conn:
        conn.execute(
            "UPDATE conversations SET messages = ?, model = ?, updated_at = ? WHERE id = ?",
            (json.dumps(messages, ensure_ascii=False), model, now, conv_id),
        )
    return {"ok": True}


@app.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    with db_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    return {"ok": True}


@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    lang = data.get("lang", "ja")

    if not text or len(text) > 1000:
        return {"error": "Text required (max 1000 chars)"}, 400

    try:
        lang_map = {"ja": "ja", "en": "en", "en-US": "en"}
        tts_lang = lang_map.get(lang, "ja")

        tts_obj = gTTS(text=text, lang=tts_lang, slow=False)
        audio_buffer = io.BytesIO()
        tts_obj.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        return Response(audio_buffer.read(), mimetype="audio/mpeg")
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
