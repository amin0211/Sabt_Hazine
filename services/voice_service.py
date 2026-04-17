import platform
import requests
from queue import Queue
import threading



# ---------------- تشخیص پلتفرم ----------------
def is_desktop():
    return platform.system().lower() == "windows"

def is_android():
    # در Flet Android معمولاً Linux گزارش می‌شود
    return platform.system().lower() == "linux"


# ---------------- ارسال به سرور ----------------
def send_audio_to_server(file_path):
    
    url = "https://your-api.com/voice-to-text"

    with open(file_path, "rb") as f:
        r = requests.post(url, files={"file": f})

    return r.json()["text"]


# ---------------- حالت Desktop ----------------
def desktop_voice(q):
    import speech_recognition as sr
    
    try:
        r = sr.Recognizer()

        # 👇 تست قبل از استفاده
        mics = sr.Microphone.list_microphone_names()
        print("MICS:", mics)

        if not mics:
            raise Exception("No microphone found")

        with sr.Microphone() as source:
            audio = r.listen(source, timeout=10)

        text = r.recognize_google(audio, language="fa-IR")
        q.put(("ok", text))

    except Exception as e:
        q.put(("error", "MIC ERROR: " + str(e)))

# ---------------- حالت Android ----------------
def android_voice(q: Queue):
    try:
        # اینجا باید فایل ضبط شده داشته باشی
        file_path = "recorded.wav"   # 👈 بعداً وصل می‌کنیم به recorder

        text = send_audio_to_server(file_path)

        q.put(("ok", text))

    except Exception as e:
        q.put(("error", str(e)))


# ---------------- تابع اصلی ----------------
def start_voice(q):
    def run():
        try:
            if is_desktop():
                desktop_voice(q)
            else:
                q.put(("error", "Voice not supported on this device yet"))
        except Exception as e:
            q.put(("error", str(e)))

    threading.Thread(target=run, daemon=True).start()