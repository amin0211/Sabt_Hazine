# Introduction

CostioIosVoice for Flet.

## Examples

```
import flet as ft

from costio_ios_voice import CostioIosVoice


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page.add(

                ft.Container(height=150, width=300, alignment = ft.Alignment.CENTER, bgcolor=ft.Colors.PURPLE_200, content=CostioIosVoice(
                    tooltip="My new CostioIosVoice Control tooltip",
                    value = "My new CostioIosVoice Flet Control",
                ),),

    )


ft.run(main)
```

## Classes

[CostioIosVoice](CostioIosVoice.md)
