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
from services.supabase_service import insert_log
import asyncio


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

# lazy desktop audio libs
sd = None
sf = None
np = None
_permission_handler = None
_audio_recorder = None

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


def _ensure_desktop_audio_libs():
    global sd, sf, np

    if sd is not None and sf is not None and np is not None:
        return

    import sounddevice as _sd
    import soundfile as _sf
    import numpy as _np

    sd = _sd
    sf = _sf
    np = _np


def _get_output_path():
    filename = f"voice_{uuid.uuid4().hex}.wav"
    return os.path.join(os.getcwd(), filename)


# ---------------- ارسال به سرور ----------------
def send_audio_to_server(file_path):
    try:

        with open(file_path, "rb") as f:
            r = requests.post(
                VOICE_API_URL,
                files={"file": f},
                timeout=30,
            )

        print("SERVER STATUS:", r.status_code)
        print("SERVER RESPONSE:", r.text)

        # اول سعی کن json را بخوانی
        data = {}
        try:
            data = r.json()
        except Exception:
            data = {}

        # اگر سرور خطا داد، پیام مناسب برگردان
        if r.status_code >= 400:
            server_error = data.get("error") or r.text

            if "Speech not understood" in str(server_error):
                return "صدای شما واضح تشخیص داده نشد. دوباره آرام‌تر و واضح‌تر بگویید."

            return f"SERVER ERROR: {server_error}"

        return data.get("text", "")

    except Exception as e:
        import traceback
        print("SEND AUDIO ERROR:", type(e).__name__, str(e))
        traceback.print_exc()
        raise


# ---------------- حالت Desktop ----------------
def list_input_devices():
    _ensure_desktop_audio_libs()

    devices = sd.query_devices()
    result = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            result.append((i, dev["name"]))
    return result


def start_desktop_recording(q: Queue):
    global _desktop_stream, _desktop_frames, _desktop_output_path

    try:
        _ensure_desktop_audio_libs()

        if _desktop_stream is not None:
            return

        _desktop_frames = []
        _desktop_output_path = _get_output_path()

        print("DESKTOP INPUT DEVICES:", list_input_devices())

        def audio_callback(indata, frames, time_info, status):
            if status:
                print("DESKTOP AUDIO STATUS:", status)
            _desktop_frames.append(indata.copy())

        _desktop_stream = sd.InputStream(
            samplerate=_desktop_samplerate,
            channels=_desktop_channels,
            dtype="float32",
            callback=audio_callback,
            device=_desktop_device_index,
        )

        _desktop_stream.start()
        print("DESKTOP: recording started")

    except Exception as e:
        q.put(("error", f"START DESKTOP ERROR: {type(e).__name__}: {e}"))


def stop_desktop_recording(q: Queue):
    global _desktop_stream, _desktop_frames, _desktop_output_path

    try:
        _ensure_desktop_audio_libs()

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

def _get_or_create_permission_handler(page):
    global _permission_handler

    if _permission_handler is None:
        _permission_handler = fph.PermissionHandler()

    if _permission_handler not in page.services:
        page.services.append(_permission_handler)

    return _permission_handler

def _get_or_create_audio_recorder(page):
    global _audio_recorder

    if _audio_recorder is None:
        _audio_recorder = far.AudioRecorder()

    if _audio_recorder not in page.services:
        page.services.append(_audio_recorder)

    return _audio_recorder
# ---------------- حالت Android ----------------

async def start_android_recording(q: Queue):
    global _current_output_path

    try:
        insert_log("ANDROID START: entered", "")

        page = _get_page()
        insert_log(f"ANDROID START: page = {page}", "")

        if page is None:
            insert_log("ANDROID START: page is None", "")
            q.put(("error", "Flet page is not available"))
            return

        permission_handler = _get_or_create_permission_handler(page)
        audio_recorder = _get_or_create_audio_recorder(page)
        insert_log("ANDROID START: services ready", "")

        perm = await permission_handler.request(fph.Permission.MICROPHONE)
        insert_log(f"ANDROID START: permission raw = {perm}", "")

        perm_name = getattr(perm, "name", str(perm)).lower()
        insert_log(f"ANDROID START: permission normalized = {perm_name}", "")

        if "granted" not in perm_name and "limited" not in perm_name:
            insert_log("ANDROID START: permission denied", "")
            q.put(("error", "Microphone permission denied"))
            return

        _current_output_path = _get_output_path()
        insert_log(f"ANDROID START: output path = {_current_output_path}", "")

        await audio_recorder.start_recording(
            output_path=_current_output_path
        )

        insert_log("ANDROID START: recording started successfully", "")

    except Exception as e:
        import traceback
        insert_log(f"ANDROID START ERROR: {type(e).__name__}: {e}", "")
        traceback.print_exc()
        q.put(("error", f"START ANDROID ERROR: {type(e).__name__}: {e}"))


async def stop_android_recording(q: Queue):
    global _current_output_path

    try:
        insert_log("ANDROID STOP: entered", "")

        page = _get_page()
        insert_log(f"ANDROID STOP: page = {page}", "")

        if page is None:
            insert_log("ANDROID STOP: page is None", "")
            q.put(("error", "Flet page is not available"))
            return

        audio_recorder = _get_or_create_audio_recorder(page)
        insert_log("ANDROID STOP: recorder ready", "")

        saved_path = await audio_recorder.stop_recording()
        insert_log(f"ANDROID STOP: saved_path = {saved_path}", "")
        insert_log(f"ANDROID STOP: fallback current path = {_current_output_path}", "")

        candidate_paths = []

        if saved_path:
            candidate_paths.append(saved_path)

        if _current_output_path:
            candidate_paths.append(_current_output_path)

        final_path = None
        for p in candidate_paths:
            if p and os.path.exists(p):
                final_path = p
                break

        insert_log(f"ANDROID STOP: chosen final_path = {final_path}", "")

        if not final_path:
            insert_log("ANDROID STOP: no valid file path found", "")
            q.put(("error", "Recorded file not found"))
            return

        try:
            file_size = os.path.getsize(final_path)
            insert_log(f"ANDROID STOP: file size = {file_size}", "")
        except Exception as e:
            insert_log(f"ANDROID STOP: getsize error = {e}", "")

        text = await asyncio.to_thread(send_audio_to_server, final_path)
        insert_log(f"ANDROID STOP: server text = {text}", "")

        if not text:
            q.put(("error", "MIC ERROR: سرور متن خالی برگرداند"))
            return

        q.put(("ok", text))

    except Exception as e:
        import traceback
        insert_log(f"ANDROID STOP ERROR: {type(e).__name__}: {e}", "")
        traceback.print_exc()
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
        insert_log("STOP RECORDING: entered", "")

        if is_android():
            insert_log("STOP RECORDING: android branch", "")
            await stop_android_recording(q)
            return

        if is_desktop():
            insert_log("STOP RECORDING: desktop branch", "")
            await asyncio.to_thread(stop_desktop_recording, q)
            return

        insert_log("STOP RECORDING: unsupported device", "")
        q.put(("error", "Voice not supported on this device yet"))

    except Exception as e:
        insert_log(f"STOP ERROR: {type(e).__name__}: {e}", "")
        q.put(("error", f"STOP ERROR: {type(e).__name__}: {e}"))

# ---------------- سازگاری با نسخه قبلی ----------------
def start_voice(q: Queue):
    page = _get_page()
    if page is None:
        q.put(("error", "Flet page context is not available"))
        return

    page.run_task(start_recording, q)