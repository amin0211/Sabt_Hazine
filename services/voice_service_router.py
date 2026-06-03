import inspect
import flet as ft


def is_android(page: ft.Page) -> bool:
    try:
        return page.platform == ft.PagePlatform.ANDROID
    except Exception:
        return False


def is_ios(page: ft.Page) -> bool:
    try:
        return page.platform == ft.PagePlatform.IOS
    except Exception:
        return False


async def _call_maybe_async(func, *args, **kwargs):
    result = func(*args, **kwargs)

    if inspect.isawaitable(result):
        return await result

    return result


async def start_recording(page: ft.Page):
    if is_ios(page):
        print("[VOICE ROUTER] platform=IOS start", flush=True)
        from services.voice_service_ios import start_recording as start_ios_recording
        return await _call_maybe_async(start_ios_recording, page)

    if is_android(page):
        print("[VOICE ROUTER] platform=ANDROID start", flush=True)
        from services.voice_service_android import start_recording as start_android_recording
        return await _call_maybe_async(start_android_recording, page)

    print("[VOICE ROUTER] platform=DESKTOP start", flush=True)
    from services.voice_service_desktop import start_recording as start_desktop_recording
    return await _call_maybe_async(start_desktop_recording, page)


async def stop_recording(page: ft.Page):
    if is_ios(page):
        print("[VOICE ROUTER] platform=IOS stop", flush=True)
        from services.voice_service_ios import stop_recording as stop_ios_recording
        return await _call_maybe_async(stop_ios_recording, page)

    if is_android(page):
        print("[VOICE ROUTER] platform=ANDROID stop", flush=True)
        from services.voice_service_android import stop_recording as stop_android_recording
        return await _call_maybe_async(stop_android_recording, page)

    print("[VOICE ROUTER] platform=DESKTOP stop", flush=True)
    from services.voice_service_desktop import stop_recording as stop_desktop_recording
    return await _call_maybe_async(stop_desktop_recording, page)