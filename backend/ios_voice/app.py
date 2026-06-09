from flask import Flask, request, jsonify
from datetime import datetime, timezone
from supabase import create_client
import tempfile
from openai import OpenAI
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

supabase_admin = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    else None
)

AUDIO_BUCKET = "financial-insight-audio"


def normalize_persian_expense_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.strip()

    fixes = {
        "دالر": "دلار",
        "دولر": "دلار",
        "دولار": "دلار",
        "نهار": "ناهار",
        "سد": "صد",
        "سدو": "صد و",
        "سد و": "صد و",
        "سوپر مارکت": "سوپرمارکت",
        "صبحانهه": "صبحانه",
        "قهوهء": "قهوه",
        "تومن": "تومان",
    }

    for wrong, correct in fixes.items():
        cleaned = cleaned.replace(wrong, correct)

    return cleaned


@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "costio-ios-voice",
        "message": "iOS voice backend is running",
    })


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "costio-ios-voice",
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
        "supabase_service_role_set": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "audio_bucket": AUDIO_BUCKET,
        "tts_route": True,
    })


@app.post("/ios-transcribe")
@app.post("/ios-transcribe/")
def ios_transcribe():
    print("IOS_TRANSCRIBE_CALLED", flush=True)

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY_MISSING", flush=True)
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY is missing on server",
        }), 500

    if "audio" not in request.files:
        print("NO_AUDIO_FILE", flush=True)
        return jsonify({
            "ok": False,
            "error": "No audio file",
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
            "size": size,
        }), 400

    try:
        prompt = (
            "این یک صدای فارسی برای ثبت هزینه در اپلیکیشن مدیریت هزینه است. "
            "گوینده معمولاً یک جمله کوتاه می‌گوید که شامل تاریخ، عنوان هزینه، مبلغ و ارز است. "
            "متن را فقط به فارسی و خیلی کوتاه بنویس. "
            "کلمات رایج: امروز، دیروز، پریروز، ناهار، شام، صبحانه، قهوه، چای، خرید، "
            "مواد غذایی، سوپرمارکت، تاکسی، اسنپ، اتوبوس، بنزین، پارکینگ، اجاره، قبض، "
            "موبایل، اینترنت، لباس، کفش، دارو، دکتر، مدرسه، دانشگاه، کتاب، رستوران. "
            "ارزهای رایج: دلار، تومان. "
            "اگر صدای عدد شنیدی، آن را دقیق به عدد بنویس؛ مثلا صد و بیست و سه را ۱۲۳ بنویس. "
            "اگر کلمه‌ای شبیه سد شنیدی، احتمالاً منظور صد است. "
            "اگر دالر، دولر یا دولار شنیدی، منظور دلار است. "
            "نمونه‌ها: امروز ناهار ۱۲۳ دلار. دیروز تاکسی ۲۵ دلار. امروز قهوه ۶ دلار. "
            "خرید مواد غذایی ۸۰ دلار. بنزین ۷۰ دلار. قبض اینترنت ۵۰ دلار."
        )

        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(

                model="gpt-4o-transcribe",

                file=f,

                language="fa",

                prompt=prompt,

            )

        raw_text = (transcription.text or "").strip()
        text = normalize_persian_expense_text(raw_text)

        print("TRANSCRIPTION_OBJECT:", transcription, flush=True)
        print("RAW_TRANSCRIBED_TEXT:", raw_text, flush=True)
        print("NORMALIZED_TRANSCRIBED_TEXT:", text, flush=True)
        print("TRANSCRIBED_TEXT_REPR:", repr(text), flush=True)

        return jsonify({
            "ok": True,
            "text": text,
            "raw_text": raw_text,
            "size": size,
        })

    except Exception as e:
        print("TRANSCRIBE_ERROR:", str(e), flush=True)

        return jsonify({
            "ok": False,
            "error": str(e),
            "size": size,
            "debug_path": audio_path,
        }), 500


@app.post("/tts-financial-insight")
@app.post("/tts-financial-insight/")
def tts_financial_insight():
    tmp_path = None

    print("TTS_FINANCIAL_INSIGHT_CALLED", flush=True)

    try:
        if not OPENAI_API_KEY:
            return jsonify({
                "ok": False,
                "error": "OPENAI_API_KEY is missing on server",
            }), 500

        if supabase_admin is None:
            return jsonify({
                "ok": False,
                "error": "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing on server",
            }), 500

        data = request.get_json(silent=True) or {}

        insight_id = data.get("insight_id")
        user_id = data.get("user_id")
        text = (data.get("text") or "").strip()

        if not insight_id:
            return jsonify({
                "ok": False,
                "error": "insight_id is required",
            }), 400

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "user_id is required",
            }), 400

        if not text:
            return jsonify({
                "ok": False,
                "error": "text is required",
            }), 400

        if len(text) > 2500:
            text = text[:2500]

        filename = (
            f"{user_id}/"
            f"{insight_id}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:8]}.mp3"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="marin",
            input=text,
            instructions=(
                "Speak in Persian in a warm, clear, calm financial assistant voice. "
                "Make it natural, smooth, and easy to understand."
            ),
            response_format="mp3",
        )

        speech.stream_to_file(tmp_path)

        with open(tmp_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        supabase_admin.storage.from_(AUDIO_BUCKET).upload(
            path=filename,
            file=audio_bytes,
            file_options={
                "content-type": "audio/mpeg",
                "upsert": "true",
            },
        )

        audio_url = supabase_admin.storage.from_(AUDIO_BUCKET).get_public_url(filename)

        supabase_admin.table("financial_insights").update({
            "audio_url": audio_url,
            "audio_storage_path": filename,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", insight_id).eq("user_id", user_id).execute()

        print("TTS_FINANCIAL_INSIGHT_OK:", filename, flush=True)

        return jsonify({
            "ok": True,
            "audio_url": audio_url,
            "audio_storage_path": filename,
        })

    except Exception as e:
        print("TTS_FINANCIAL_INSIGHT_ERROR:", str(e), flush=True)

        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass



if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)