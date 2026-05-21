from flask import Flask, request, jsonify
from openai import OpenAI
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "costio-ios-voice",
        "message": "iOS voice backend is running"
    })


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY"))
    })


@app.post("/ios-transcribe")
def ios_transcribe():
    print("IOS_TRANSCRIBE_CALLED", flush=True)

    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY is missing on server"
        }), 500

    if "audio" not in request.files:
        return jsonify({
            "ok": False,
            "error": "No audio file"
        }), 400

    audio_file = request.files["audio"]

    debug_dir = os.path.join(os.getcwd(), "debug_audio_uploads")
    os.makedirs(debug_dir, exist_ok=True)

    audio_path = os.path.join(
        debug_dir,
        f"ios_audio_{uuid.uuid4().hex}.m4a"
    )

    audio_file.save(audio_path)
    size = os.path.getsize(audio_path)

    print("AUDIO_FILENAME:", audio_file.filename, flush=True)
    print("AUDIO_CONTENT_TYPE:", audio_file.content_type, flush=True)
    print("AUDIO_SAVED_PATH:", audio_path, flush=True)
    print("AUDIO_SIZE:", size, flush=True)

    if size <= 0:
        return jsonify({
            "ok": False,
            "error": "Audio file is empty",
            "size": size
        }), 400

    try:
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="fa",
                prompt=(
                    "این یک صدای فارسی برای ثبت هزینه در اپلیکیشن مدیریت هزینه است. "
                    "متن معمولاً شامل تاریخ، عنوان هزینه، مبلغ و ارز است. "
                    "مثال‌ها: امروز ناهار ۱۲۳ دلار. دیروز تاکسی ۲۵ دلار. "
                    "امروز قهوه ۶ دلار. خرید مواد غذایی ۸۰ دلار. "
                    "کلمات رایج: امروز، دیروز، ناهار، شام، صبحانه، خرید، تاکسی، "
                    "بنزین، قهوه، مواد غذایی، دلار، تومان. "
                    "متن را کوتاه، واضح و فارسی بنویس."
                ),
            )

        text = (transcription.text or "").strip()

        print("TRANSCRIBED_TEXT:", text, flush=True)
        print("TRANSCRIBED_TEXT_REPR:", repr(text), flush=True)

        return jsonify({
            "ok": True,
            "text": text,
            "size": size
        })

    except Exception as e:
        print("TRANSCRIBE_ERROR:", str(e), flush=True)
        return jsonify({
            "ok": False,
            "error": str(e),
            "size": size,
            "debug_path": audio_path
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
