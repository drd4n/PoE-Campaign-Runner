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

# Size carries priority: the step you're on is the biggest thing in the panel,
# what's coming sits back, and done steps are history — worth seeing, not worth
# reading. The bullets keep the label's own size, since they're the instructions
# you actually follow.
CURRENT_FONT_SIZE = 12.0
UPCOMING_FONT_SIZE = 9.5
DONE_FONT_SIZE = 8.0
DONE_LINE_HEIGHT = "1.15"
UPCOMING_LINE_HEIGHT = "1.3"

_CHAR_W = 0.55  # Consolas advance width, in em
_MARKER_SLOT = 2 * _CHAR_W * CURRENT_FONT_SIZE  # "✓ " at the largest size


# Indentation separates the three tiers as much as size does: upcoming steps run
# flush to the edge as a plain list of what's next, the current step is pushed in
# to stand clear of them, and its objectives are nested further still. Optional
# detours keep their ○ marker, which reads as a branch off the current line.
UPCOMING_INDENT = "0px"
CURRENT_INDENT = "6px"
BULLET_INDENT = "22px"


def _indent(font_size: float) -> str:
    """Left pad for a row at this size.

    Each row starts with a marker and a space, so a smaller row's text would
    begin further left than a larger one's. Padding the difference keeps every
    step's text in the same column whatever size it renders at.
    """
    return f"{max(0.0, _MARKER_SLOT - 2 * _CHAR_W * font_size):.1f}px"

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
            lines.append(
                f'<div style="color:{DONE_COLOR}; font-size:{DONE_FONT_SIZE}px;'
                f" line-height:{DONE_LINE_HEIGHT}; padding-left:{_indent(DONE_FONT_SIZE)};\">"
                f"{TICK} {text}</div>"
            )
        elif i == pointer:
            lines.append(
                f'<div style="color:{CURRENT_COLOR}; font-size:{CURRENT_FONT_SIZE}px;'
                f' padding-left:{CURRENT_INDENT};"><b>{POINTER} {text}</b></div>'
            )
            lines.extend(_bullets(step))
        else:
            colour = OPTIONAL_COLOR if step.optional else UPCOMING_COLOR
            marker = f"{OPTIONAL} " if step.optional else ""
            lines.append(
                f'<div style="color:{colour}; font-size:{UPCOMING_FONT_SIZE}px;'
                f' line-height:{UPCOMING_LINE_HEIGHT};'
                f' padding-left:{UPCOMING_INDENT};">{marker}{text}</div>'
            )
    return "".join(lines)


def _bullets(step) -> list[str]:
    out = []
    for j, bullet in enumerate(step.bullets):
        per_league = j in step.per_league
        colour = PER_LEAGUE_COLOR if per_league else BULLET_COLOR
        marker = PER_LEAGUE if per_league else BULLET
        out.append(
            f'<div style="color:{colour}; margin-left:{BULLET_INDENT};">'
            f"{marker} {escape(bullet)}</div>"
        )
    return out


def header_text(act: int, off_route: bool) -> str:
    return f"Act {act}" + ("  ·  off route" if off_route else "")


def progress_text(progress: tuple[int, int]) -> str:
    done, total = progress
    return f"[{done}/{total}]"
