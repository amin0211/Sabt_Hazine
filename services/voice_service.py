import os
import uuid
import platform
import threading
from queue import Queue

import requests
import numpy as np
import sounddevice as sd
import soundfile as sf

# Flet imports for Android/mobile path
import flet as ft
from flet import context

import flet_audio_recorder as far
import flet_permission_handler as fph


# ---------------- تنظیمات ----------------
VOICE_API_URL = "https://sabt-hazine-service.onrender.com/parse"
# VOICE_API_URL = "http://127.0.0.1:5000/parse"

# global singletons per app session
_permission_handler = None
_audio_recorder = None
_services_initialized = False

# desktop globals
_desktop_stream = None
_desktop_frames = []
_desktop_samplerate = 16000
_desktop_channels = 1
_desktop_output_path = None
_desktop_device_index = None  # اگر خواستی دستی تنظیمش کن

# current recorded file path (android)
_current_output_path = None


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
    return _is_flet_windows() or _is_plain_windows()


def is_android():
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
    filename = f"voice_{uuid.uuid4().hex}.wav"
    return os.path.join(os.getcwd(), filename)


# ---------------- ارسال به سرور ----------------

def send_audio_to_server(file_path):
    with open(file_path, "rb") as f:
        r = requests.post(
            "http://127.0.0.1:5000/parse",
            files={"file": f},
            timeout=120,
        )

    print("SERVER STATUS:", r.status_code)
    print("SERVER RESPONSE:", r.text)

    r.raise_for_status()

    data = r.json()
    return data.get("text", "")


# ---------------- حالت Desktop ----------------
def list_input_devices():
    devices = sd.query_devices()
    result = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            result.append((i, dev["name"]))
    return result


def start_desktop_recording(q: Queue):
    global _desktop_stream, _desktop_frames, _desktop_output_path

    try:
        if _desktop_stream is not None:
            return

        _desktop_frames = []
        _desktop_output_path = _get_output_path()

        print("DESKTOP INPUT DEVICES:", list_input_devices())

        def audio_callback(indata, frames, time, status):
            if status:
                print("DESKTOP AUDIO STATUS:", status)
            _desktop_frames.append(indata.copy())

        _desktop_stream = sd.InputStream(
            samplerate=_desktop_samplerate,
            channels=_desktop_channels,
            dtype="float32",
            callback=audio_callback,
            device=_desktop_device_index,   # اگر None باشد پیش‌فرض سیستم
        )

        _desktop_stream.start()
        print("DESKTOP: recording started")

    except Exception as e:
        q.put(("error", f"START DESKTOP ERROR: {type(e).__name__}: {e}"))


def stop_desktop_recording(q: Queue):
    global _desktop_stream, _desktop_frames, _desktop_output_path

    try:
        if _desktop_stream is None:
            q.put(("error", "STOP DESKTOP ERROR: stream is not running"))
            return

        _desktop_stream.stop()
        _desktop_stream.close()
        _desktop_stream = None
        print("DESKTOP: recording stopped")

        if not _desktop_frames:
            q.put(("error", "MIC ERROR: هیچ صدایی ضبط نشد"))
            return

        audio_data = np.concatenate(_desktop_frames, axis=0)

        if len(audio_data) < 1000:
            q.put(("error", "MIC ERROR: مدت ضبط خیلی کوتاه بود"))
            return

        sf.write(_desktop_output_path, audio_data, _desktop_samplerate)
        print("DESKTOP WAV PATH:", _desktop_output_path)

        print("DESKTOP: sending wav to server...")
        text = send_audio_to_server(_desktop_output_path)
        print("DESKTOP RESULT:", text)

        if not text:
            q.put(("error", "MIC ERROR: سرور متن خالی برگرداند"))
            return

        q.put(("ok", text))

    except Exception as e:
        import traceback
        print("STOP DESKTOP ERROR:", type(e).__name__, str(e))
        traceback.print_exc()
        q.put(("error", f"STOP DESKTOP ERROR: {type(e).__name__}: {e}"))

# ---------------- حالت Android ----------------
async def start_android_recording(q: Queue):
    global _current_output_path

    try:
        page = _get_page()
        if page is None:
            q.put(("error", "Flet page is not available"))
            return

        _ensure_services()

        perm = await _permission_handler.request(fph.Permission.MICROPHONE)
        perm_name = getattr(perm, "name", str(perm)).lower()

        if "granted" not in perm_name and "limited" not in perm_name:
            q.put(("error", "Microphone permission denied"))
            return

        _current_output_path = _get_output_path()

        await _audio_recorder.start_recording(
            output_path=_current_output_path,
            android_config=far.AndroidRecorderConfiguration(
                audio_source=far.AndroidAudioSource.VOICE_RECOGNITION,
                use_legacy=True,
            ),
        )

        print("ANDROID: recording started")

    except Exception as e:
        q.put(("error", f"START ANDROID ERROR: {type(e).__name__}: {e}"))


async def stop_android_recording(q: Queue):
    global _current_output_path

    try:
        page = _get_page()
        if page is None:
            q.put(("error", "Flet page is not available"))
            return

        saved_path = await _audio_recorder.stop_recording()
        final_path = saved_path or _current_output_path

        print("ANDROID: recording stopped")
        print("ANDROID PATH:", final_path)

        if not final_path or not os.path.exists(final_path):
            q.put(("error", "Recorded file not found"))
            return

        def worker():
            return send_audio_to_server(final_path)

        text = await page.run_thread(worker)
        print("ANDROID RESULT:", text)
        q.put(("ok", text))

    except Exception as e:
        q.put(("error", f"STOP ANDROID ERROR: {type(e).__name__}: {e}"))


# ---------------- توابع اصلی برای UI ----------------
async def start_recording(q: Queue):
    try:
        if is_android():
            await start_android_recording(q)
            return

        if is_desktop():
            threading.Thread(
                target=lambda: start_desktop_recording(q),
                daemon=True
            ).start()
            return

        q.put(("error", "Voice not supported on this device yet"))

    except Exception as e:
        q.put(("error", f"START ERROR: {type(e).__name__}: {e}"))


async def stop_recording(q: Queue):
    try:
        if is_android():
            await stop_android_recording(q)
            return

        if is_desktop():
            threading.Thread(
                target=lambda: stop_desktop_recording(q),
                daemon=True
            ).start()
            return

        q.put(("error", "Voice not supported on this device yet"))

    except Exception as e:
        q.put(("error", f"STOP ERROR: {type(e).__name__}: {e}"))


# ---------------- سازگاری با نسخه قبلی ----------------
def start_voice(q: Queue):
    page = _get_page()
    if page is None:
        q.put(("error", "Flet page context is not available"))
        return

    page.run_task(start_recording, q)