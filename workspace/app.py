import json
import urllib.request
from flask import Flask, render_template, request, Response, stream_with_context

app = Flask(__name__)
OLLAMA_URL = "http://ollama:11434/api/generate"
ALLOWED_MODELS = {"gemma4:e4b", "gemma3:4b", "gemma3:1b", "gemma3:270m"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    image_b64 = data.get("image")
    file_text = (data.get("file_text") or "").strip()
    file_name = (data.get("file_name") or "ファイル").strip()
    model = data.get("model") if data.get("model") in ALLOWED_MODELS else "gemma4:e4b"

    if not prompt and not image_b64 and not file_text:
        return Response("data: [DONE]\n\n", mimetype="text/event-stream")

    if file_text:
        prompt = f"[添付ファイル: {file_name}]\n---\n{file_text}\n---\n\n{prompt}"

    think = bool(data.get("think", False))
    payload = {"model": model, "prompt": prompt, "stream": True, "think": think}
    if image_b64:
        payload["images"] = [image_b64]

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
                    thinking = chunk.get("thinking", "")
                    token = chunk.get("response", "")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
