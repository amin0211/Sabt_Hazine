import os
import uuid
import time
import platform
import requests


VOICE_API_URL = "https://sabt-hazine-service.onrender.com/parse"

# Lazy desktop audio libs
sd = None
sf = None
np = None

# Desktop recording state
_desktop_stream = None
_desktop_frames = []
_desktop_samplerate = 16000
_desktop_channels = 1
_desktop_output_path = None
_desktop_start_time = None
_desktop_device_index = None  # اگر لازم شد دستی ست کن


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


def is_desktop() -> bool:
    return platform.system().lower() in ["windows", "darwin", "linux"]


def _get_output_path() -> str:
    folder = os.path.join(os.getcwd(), "recordings")
    os.makedirs(folder, exist_ok=True)

    filename = f"voice_{uuid.uuid4().hex}.wav"
    return os.path.join(folder, filename)


def send_audio_to_server(file_path: str) -> str:
    with open(file_path, "rb") as f:
        response = requests.post(
            VOICE_API_URL,
            files={"file": f},
            timeout=30,
        )

    try:
        data = response.json()
    except Exception:
        data = {}

    if response.status_code >= 400:
        server_error = data.get("error") or response.text

        if "Speech not understood" in str(server_error):
            return "صدای شما واضح تشخیص داده نشد. دوباره آرام‌تر و واضح‌تر بگویید."

        return f"SERVER ERROR: {server_error}"

    return data.get("text", "")


def list_input_devices():
    _ensure_desktop_audio_libs()

    devices = sd.query_devices()
    result = []

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            result.append((i, dev["name"]))

    return result


def start_recording(page=None):
    global _desktop_stream
    global _desktop_frames
    global _desktop_output_path
    global _desktop_start_time

    try:
        _ensure_desktop_audio_libs()

        if _desktop_stream is not None:
            return {
                "ok": False,
                "message": "Desktop recording is already running",
                "path": None,
            }

        _desktop_frames = []
        _desktop_output_path = _get_output_path()
        _desktop_start_time = time.time()

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
        print("DESKTOP WAV TARGET:", _desktop_output_path)

        return {
            "ok": True,
            "message": "Desktop recording started",
            "path": None,
        }

    except Exception as e:
        import traceback
        print("START DESKTOP ERROR:", type(e).__name__, str(e))
        traceback.print_exc()

        _reset_desktop_state()

        return {
            "ok": False,
            "message": f"START DESKTOP ERROR: {type(e).__name__}: {e}",
            "path": None,
        }


def stop_recording(page=None):
    global _desktop_stream
    global _desktop_frames
    global _desktop_output_path
    global _desktop_start_time

    try:
        _ensure_desktop_audio_libs()

        if _desktop_stream is None:
            return {
                "ok": False,
                "message": "STOP DESKTOP ERROR: stream is not running",
                "path": None,
            }

        _desktop_stream.stop()
        _desktop_stream.close()
        _desktop_stream = None

        print("DESKTOP: recording stopped")

        if not _desktop_frames:
            _reset_desktop_state()
            return {
                "ok": False,
                "message": "MIC ERROR: هیچ صدایی ضبط نشد",
                "path": None,
            }

        audio_data = np.concatenate(_desktop_frames, axis=0)

        if len(audio_data) < 1000:
            _reset_desktop_state()
            return {
                "ok": False,
                "message": "MIC ERROR: مدت ضبط خیلی کوتاه بود",
                "path": None,
            }

        if not _desktop_output_path:
            _reset_desktop_state()
            return {
                "ok": False,
                "message": "STOP DESKTOP ERROR: output path is empty",
                "path": None,
            }

        sf.write(_desktop_output_path, audio_data, _desktop_samplerate)

        duration = 0
        if _desktop_start_time:
            duration = time.time() - _desktop_start_time

        print("DESKTOP WAV PATH:", _desktop_output_path)
        print("DESKTOP DURATION:", duration)

        text = ""

        try:
            print("DESKTOP: sending wav to server...")
            text = send_audio_to_server(_desktop_output_path)
            print("DESKTOP RESULT:", text)
        except Exception as server_error:
            print("DESKTOP SERVER ERROR:", type(server_error).__name__, str(server_error))
            text = ""

        result = {
            "ok": True,
            "message": "Desktop recording stopped",
            "path": _desktop_output_path,
            "duration": duration,
            "text": text,
        }

        _reset_desktop_state(keep_file_path=True)

        return result

    except Exception as e:
        import traceback
        print("STOP DESKTOP ERROR:", type(e).__name__, str(e))
        traceback.print_exc()

        _reset_desktop_state()

        return {
            "ok": False,
            "message": f"STOP DESKTOP ERROR: {type(e).__name__}: {e}",
            "path": None,
        }


def _reset_desktop_state(keep_file_path=False):
    global _desktop_stream
    global _desktop_frames
    global _desktop_output_path
    global _desktop_start_time

    try:
        if _desktop_stream is not None:
            _desktop_stream.stop()
            _desktop_stream.close()
    except Exception:
        pass

    _desktop_stream = None
    _desktop_frames = []
    _desktop_start_time = None

    if not keep_file_path:
        _desktop_output_path = None