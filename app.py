from flask import Flask, request, jsonify
import tempfile
import os
from openai import OpenAI

# ⬇️ اینو اضافه کن
from services.parser_service import parse_expense


app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ===============================
# 🎤 VOICE → TEXT
# ===============================
@app.route("/voice-to-text", methods=["POST"])
def voice_to_text():
    try:
        file = request.files["file"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            file.save(temp.name)
            path = temp.name

        with open(path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio
            )

        os.remove(path)

        return jsonify({"text": transcript.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# 🧠 TEXT → PARSE EXPENSE
# ===============================
@app.route("/parse", methods=["POST"])
def parse_text():
    try:
        data = request.get_json()
        text = data.get("text", "")

        result = parse_expense(text)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# 🔄 VOICE → TEXT → PARSE (خیلی مهم)
# ===============================
@app.route("/voice-parse", methods=["POST"])
def voice_parse():
    try:
        file = request.files["file"]

        # 1. save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            file.save(temp.name)
            path = temp.name

        # 2. speech to text
        with open(path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio
            )

        os.remove(path)

        text = transcript.text

        # 3. parse text
        parsed = parse_expense(text)

        return jsonify({
            "text": text,
            "parsed": parsed
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# ❤️ HEALTH CHECK
# ===============================
@app.route("/")
def home():
    return "🚀 Server is running"


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    })


# ===============================
# ▶ RUN
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)