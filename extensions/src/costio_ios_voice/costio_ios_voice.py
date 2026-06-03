from typing import Optional

import flet as ft


@ft.control("CostioIosVoice")
class CostioIosVoice(ft.LayoutControl):
    command: str = ""
    backend_url: str = ""
    value: str = ""

    on_result: Optional[ft.ControlEventHandler] = None