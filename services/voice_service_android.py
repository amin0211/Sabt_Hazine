import asyncio
from flet_stt import FletStt, SttResult, SttErrorData


_state = {
    "stt": None,
    "future": None,
    "listening": False,
}


async def start_recording(page):
    loop = asyncio.get_running_loop()

    future = loop.create_future()
    _state["future"] = future
    _state["listening"] = True

    stt = FletStt()
    _state["stt"] = stt

    async def on_result(e):
        r = SttResult(e)

        if r.text and r.final:
            if not future.done():
                future.set_result({
                    "ok": True,
                    "text": r.text,
                })

            _state["listening"] = False
            try:
                await stt.stop()
            except:
                pass

    async def on_error(e):
        err = SttErrorData(e)

        if err.error == "error-no-match" and _state["listening"]:
            try:
                await stt.listen(
                    locale_id="fa_IR",
                    listen_mode="dictation",
                    partial_results=True,
                    on_device=False,
                )
            except Exception as ex:
                if not future.done():
                    future.set_result({
                        "ok": False,
                        "error": str(ex),
                    })
        else:
            if not future.done():
                future.set_result({
                    "ok": False,
                    "error": err.error,
                })

            _state["listening"] = False

    stt.on_result = on_result
    stt.on_error = on_error

    ok = await stt.initialize()
    if not ok:
        _state["listening"] = False
        if not future.done():
            future.set_result({
                "ok": False,
                "error": "microphone_permission_denied",
            })
        return {"ok": False, "error": "microphone_permission_denied"}

    await stt.listen(
        locale_id="fa_IR",
        listen_mode="dictation",
        partial_results=True,
        on_device=False,
    )

    return {"ok": True, "started": True}


async def stop_recording(page):
    future = _state.get("future")
    stt = _state.get("stt")

    _state["listening"] = False

    try:
        if stt:
            await stt.stop()
    except:
        pass

    if future:
        try:
            return await asyncio.wait_for(future, timeout=1.5)
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "error": "no_text_received",
            }

    return {
        "ok": False,
        "error": "stt_not_started",
    }