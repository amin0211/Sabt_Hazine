import asyncio

from services.supabase_service import sign_out_user
from services.auth_session import clear_session_storage


async def logout_async(page):
    try:
        await asyncio.to_thread(sign_out_user)
    except Exception as ex:
        print("[LOGOUT] sign_out error:", ex, flush=True)

    try:
        await clear_session_storage(page)
        print("[LOGOUT] session storage cleared", flush=True)
    except Exception as ex:
        print("[LOGOUT] clear storage error:", ex, flush=True)

    page.data = {}
    page.app_go("login")


def logout(page):
    page.run_task(logout_async, page)