"""Rendering for the act checklist.

Pure string building, no Qt — so the view can be tested without a display.
QLabel renders a subset of HTML, which is what lets each line carry its own
colour.
"""
from html import escape

DONE_COLOR = "#5c5c5c"
CURRENT_COLOR = "#e8c97a"
UPCOMING_COLOR = "#b0b0b0"
BULLET_COLOR = "#dddddd"
PER_LEAGUE_COLOR = "#8a9bb0"
OPTIONAL_COLOR = "#8f8a72"
OFF_ROUTE_COLOR = "#c98a5a"

TICK = "&#10003;"      # ✓ done
POINTER = "&#9654;"    # ▶ current
OPTIONAL = "&#9675;"   # ○ optional detour
PER_LEAGUE = "&#8634;"  # ⟲ once per league
BULLET = "&bull;"


def checklist_html(steps, pointer: int) -> str:
    """Done steps ticked and collapsed, the current step expanded into
    bullets, upcoming steps collapsed."""
    lines = []
    for i, step in enumerate(steps):
        text = escape(step.short)
        if i < pointer:
            lines.append(f'<div style="color:{DONE_COLOR};">{TICK} {text}</div>')
        elif i == pointer:
            lines.append(
                f'<div style="color:{CURRENT_COLOR};"><b>{POINTER} {text}</b></div>'
            )
            lines.extend(_bullets(step))
        else:
            colour = OPTIONAL_COLOR if step.optional else UPCOMING_COLOR
            marker = OPTIONAL if step.optional else "&nbsp;&nbsp;"
            lines.append(f'<div style="color:{colour};">{marker} {text}</div>')
    return "".join(lines)


def _bullets(step) -> list[str]:
    out = []
    for j, bullet in enumerate(step.bullets):
        per_league = j in step.per_league
        colour = PER_LEAGUE_COLOR if per_league else BULLET_COLOR
        marker = PER_LEAGUE if per_league else BULLET
        out.append(
            f'<div style="color:{colour}; margin-left:14px;">'
            f"{marker} {escape(bullet)}</div>"
        )
    return out


def header_text(act: int, off_route: bool) -> str:
    return f"Act {act}" + ("  ·  off route" if off_route else "")


def progress_text(progress: tuple[int, int]) -> str:
    done, total = progress
    return f"[{done}/{total}]"
