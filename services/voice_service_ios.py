import asyncio
import json
import time
from typing import Optional

from costio_ios_voice import CostioIosVoice


_backend_url = "https://sabthazine-production.up.railway.app/ios-transcribe"
# _backend_url = "http://10.0.0.27:5001/ios-transcribe"
                

_voice_control: Optional[CostioIosVoice] = None
_last_result: Optional[dict] = None
_result_event = asyncio.Event()
_command_counter = 0



def _ensure_voice_control(page):
    global _voice_control

    if _voice_control is not None:
        return _voice_control

    print("[IOS VOICE SERVICE] creating CostioIosVoice control", flush=True)

    def on_result(e):
        global _last_result

        print("[IOS VOICE SERVICE] result event received:", e.data, flush=True)

        try:
            _last_result = json.loads(e.data or "{}")
        except Exception as ex:
            _last_result = {
                "ok": False,
                "error": f"Invalid result JSON: {ex}",
                "raw": e.data,
            }

        try:
            _result_event.set()
        except Exception as ex:
            print("[IOS VOICE SERVICE] result_event set error:", ex, flush=True)

    _voice_control = CostioIosVoice(
        command="",
        backend_url=_backend_url,
        value="",
        on_result=on_result,
    )

    if page is not None:
        try:
            page.overlay.append(_voice_control)
            page.update()
            print("[IOS VOICE SERVICE] control added to page.overlay", flush=True)
        except Exception as ex:
            print("[IOS VOICE SERVICE] failed to add control:", ex, flush=True)

    return _voice_control


async def _send_command(page, command: str, timeout_seconds: float = 30.0):
    global _last_result, _command_counter

    control = _ensure_voice_control(page)

    _last_result = None
    _result_event.clear()

    _command_counter += 1

    # command باید هر بار عوض شود تا Dart didUpdateWidget اجرا شود
    control.command = f"{command}:{_command_counter}"
    control.backend_url = _backend_url

    print("[IOS VOICE SERVICE] sending command:", control.command, flush=True)

    if page is not None:
        page.update()

    try:
        await asyncio.wait_for(_result_event.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "error": f"Timeout waiting for iOS voice result after {command}",
        }

    return _last_result or {
        "ok": False,
        "error": "Empty iOS voice result",
    }
async def warmup_recording(page=None):
    print("[IOS VOICE SERVICE] warmup_recording called", flush=True)

    result = await _send_command(page, "warmup", timeout_seconds=20.0)

    print("[IOS VOICE SERVICE] warmup result:", result, flush=True)

    return result

async def prepare_recording(page=None):
    print("[IOS VOICE SERVICE] prepare_recording called", flush=True)

    result = await _send_command(page, "prepare", timeout_seconds=15.0)

    print("[IOS VOICE SERVICE] prepare result:", result, flush=True)

    return result


async def start_recording(page=None):
    print("[IOS VOICE SERVICE] start_recording called", flush=True)

    result = await _send_command(page, "start", timeout_seconds=10.0)

    print("[IOS VOICE SERVICE] start result:", result, flush=True)

    return result


async def stop_recording(page=None):
    print("[IOS VOICE SERVICE] stop_recording called", flush=True)

    result = await _send_command(page, "stop", timeout_seconds=60.0)

    print("[IOS VOICE SERVICE] stop result:", result, flush=True)

    return result