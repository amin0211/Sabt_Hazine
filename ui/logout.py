from services.supabase_service import sign_out_user
from services.auth_session import clear_session_storage


def logout(page):
    try:
        sign_out_user()
    except Exception:
        pass

    clear_session_storage(page)
    page.app_go("login")