from flask import Flask, request, jsonify
import tempfile
import os
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/voice-to-text", methods=["POST"])
def voice_to_text():
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