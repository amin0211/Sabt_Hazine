from flask import Flask, request, jsonify
import os
import traceback
import speech_recognition as sr

app = Flask(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/")
def home():
    return "Server is running"

@app.route("/parse", methods=["POST"])
def parse_audio():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        save_path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(save_path)

        recognizer = sr.Recognizer()

        with sr.AudioFile(save_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language="fa-IR")

        return jsonify({"text": text})

    except sr.UnknownValueError:
        return jsonify({"error": "Speech not understood"}), 400

    except sr.RequestError as e:
        return jsonify({"error": f"Speech service error: {e}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)