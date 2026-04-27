import inspect
import flet as ft

from services.voice_service_android import (
    start_recording as start_android_recording,
    stop_recording as stop_android_recording,
)

from services.voice_service_desktop import (
    start_recording as start_desktop_recording,
    stop_recording as stop_desktop_recording,
)


def is_android(page: ft.Page) -> bool:
    try:
        return page.platform == ft.PagePlatform.ANDROID
    except Exception:
        return False


async def _call_maybe_async(func, *args, **kwargs):
    result = func(*args, **kwargs)

    if inspect.isawaitable(result):
        return await result

    return result


async def start_recording(page: ft.Page):
    if is_android(page):
        return await _call_maybe_async(start_android_recording, page)

    return await _call_maybe_async(start_desktop_recording, page)


async def stop_recording(page: ft.Page):
    if is_android(page):
        return await _call_maybe_async(stop_android_recording, page)

    return await _call_maybe_async(stop_desktop_recording, page)