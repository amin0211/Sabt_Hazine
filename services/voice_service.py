import os
import uuid
import platform
import threading
from queue import Queue

import requests

# Flet imports for Android/mobile path
import flet as ft
from flet import context

import flet_audio_recorder as far
import flet_permission_handler as fph


# ---------------- تنظیمات ----------------
VOICE_API_URL = "https://your-api.com/voice-to-text"

# global singletons per app session
_permission_handler = None
_audio_recorder = None
_services_initialized = False


# ---------------- ابزارهای کمکی ----------------
def _get_page():
    try:
        return context.page
    except Exception:
        return None


def _is_flet_android():
    page = _get_page()
    return page is not None and page.platform == ft.PagePlatform.ANDROID


def _is_flet_windows():
    page = _get_page()
    return page is not None and page.platform == ft.PagePlatform.WINDOWS


def _is_plain_windows():
    return platform.system().lower() == "windows"


def is_desktop():
    # برای سازگاری با نسخه قبلی
    # اگر داخل Flet باشیم، ویندوز را از page.platform می‌گیریم
    return _is_flet_windows() or _is_plain_windows()


def is_android():
    # برای سازگاری با نسخه قبلی
    return _is_flet_android()


def _ensure_services():
    global _permission_handler, _audio_recorder, _services_initialized

    if _services_initialized:
        return

    page = _get_page()
    if page is None:
        raise RuntimeError("Flet page context is not available")

    _permission_handler = fph.PermissionHandler()
    _audio_recorder = far.AudioRecorder()

    page.services.append(_permission_handler)
    page.services.append(_audio_recorder)

    _services_initialized = True


def _get_output_path():
    # داخل پوشه جاری اپ
    filename = f"voice_{uuid.uuid4().hex}.wav"
    return os.path.join(os.getcwd(), filename)


# ---------------- ارسال به سرور ----------------
def send_audio_to_server(file_path):
    with open(file_path, "rb") as f:
        r = requests.post(
            VOICE_API_URL,
            files={"file": f},
            timeout=120,
        )
        r.raise_for_status()

    data = r.json()
    return data.get("text", "")


# ---------------- حالت Desktop ----------------
def desktop_voice(q):
    import speech_recognition as sr

    try:
        r = sr.Recognizer()

        mics = sr.Microphone.list_microphone_names()
        print("MICS:", mics)

        if not mics:
            raise Exception("No microphone found")

        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=10)

        text = r.recognize_google(audio, language="fa-IR")
        q.put(("ok", text))

    except Exception as e:
        q.put(("error", "MIC ERROR: " + str(e)))


# ---------------- حالت Android ----------------
async def _android_voice_async(q: Queue):
    try:
        page = _get_page()
        if page is None:
            q.put(("error", "Flet page is not available"))
            return

        _ensure_services()

        # درخواست دسترسی میکروفون
        perm = await _permission_handler.request(fph.Permission.MICROPHONE)
        perm_name = getattr(perm, "name", str(perm)).lower()
        if "granted" not in perm_name and "limited" not in perm_name:
            q.put(("error", "Microphone permission denied"))
            return

        output_path = _get_output_path()

        # شروع ضبط
        await _audio_recorder.start_recording(
            output_path=output_path,
            android_config=far.AndroidRecorderConfiguration(
                audio_source=far.AndroidAudioSource.VOICE_RECOGNITION,
                use_legacy=True,
            ),
        )

        # برای حفظ API فعلی بدون تغییر UI:
        # این نسخه مثل دسکتاپ یک‌مرحله‌ای نیست؛
        # حدود 6 ثانیه ضبط می‌کند و بعد می‌فرستد.
        # اگر بعداً خواستی start/stop واقعی با همان دکمه داشته باشی،
        # آن موقع باید UI کمی تغییر کند.
        import asyncio
        await asyncio.sleep(6)

        saved_path = await _audio_recorder.stop_recording()
        final_path = saved_path or output_path

        def worker():
            return send_audio_to_server(final_path)

        text = await page.run_thread(worker)
        q.put(("ok", text))

    except Exception as e:
        q.put(("error", "ANDROID ERROR: " + str(e)))


def android_voice(q: Queue):
    page = _get_page()
    if page is None:
        q.put(("error", "Android voice requires Flet page context"))
        return

    # اجرای async task بدون نیاز به تغییر UI
    page.run_task(_android_voice_async, q)


# ---------------- تابع اصلی ----------------
def start_voice(q):
    try:
        if is_android():
            android_voice(q)
            return

        if is_desktop():
            threading.Thread(target=lambda: desktop_voice(q), daemon=True).start()
            return

        q.put(("error", "Voice not supported on this device yet"))

    except Exception as e:
        q.put(("error", str(e)))