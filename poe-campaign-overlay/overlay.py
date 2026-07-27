from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPainterPath

from checklist_view import OFF_ROUTE_COLOR, checklist_html, header_text, progress_text

_WIDTH = 360
_MARGIN = 16
_PADDING = 12
_BG = QColor(10, 10, 10, 210)
_ZONE_COLOR = "#e8c97a"
_STEP_COLOR = "#cccccc"
_ACT_COLOR = "#888888"
_BTN_STYLE = """
    QPushButton {
        background: rgba(50, 50, 50, 220);
        color: #e8c97a;
        border: 1px solid #e8c97a;
        border-radius: 4px;
        padding: 5px 14px;
        font-family: Consolas;
        font-size: 10pt;
    }
    QPushButton:hover {
        background: rgba(232, 201, 122, 50);
    }
"""


class BackButton(QWidget):
    """A separate one-button window.

    The checklist itself stays click-through, so the only patch of screen that
    swallows clicks from the game is this button.
    """

    pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("◀ Back")
        button.setStyleSheet(_BTN_STYLE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip("Go back one step")
        button.clicked.connect(self.pressed.emit)
        layout.addWidget(button)
        self.adjustSize()

    def dock_under(self, panel: QWidget) -> None:
        """Sit just below the panel, left edges aligned."""
        self.adjustSize()
        self.move(panel.x(), panel.y() + panel.height() + 6)


class OverlayWindow(QWidget):
    act_selected = pyqtSignal(int)
    back_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_window()
        self._build_ui()
        self._back = BackButton()
        self._back.pressed.connect(self.back_pressed.emit)

    def _build_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool               # hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        self.setFixedWidth(_WIDTH)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_PADDING, _PADDING, _PADDING, _PADDING)
        layout.setSpacing(4)

        # Header: act on the left, checklist progress on the right.
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self._act_label = QLabel()
        self._act_label.setFont(QFont("Consolas", 9))
        self._act_label.setStyleSheet(f"color: {_ACT_COLOR}; background: transparent;")
        header_layout.addWidget(self._act_label)
        header_layout.addStretch()

        self._progress_label = QLabel()
        self._progress_label.setFont(QFont("Consolas", 9))
        self._progress_label.setStyleSheet(f"color: {_ACT_COLOR}; background: transparent;")
        header_layout.addWidget(self._progress_label)

        layout.addWidget(header)

        self._zone_label = QLabel()
        self._zone_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self._zone_label.setStyleSheet(f"color: {_ZONE_COLOR}; background: transparent;")
        self._zone_label.setWordWrap(True)
        layout.addWidget(self._zone_label)

        self._steps_label = QLabel()
        self._steps_label.setFont(QFont("Consolas", 10))
        self._steps_label.setStyleSheet(f"color: {_STEP_COLOR}; background: transparent;")
        self._steps_label.setWordWrap(True)
        self._steps_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._steps_label)

        # Container for act-selection buttons (hidden until needed)
        self._button_container = QWidget()
        self._button_container.setStyleSheet("background: transparent;")
        self._button_layout = QHBoxLayout(self._button_container)
        self._button_layout.setContentsMargins(0, 6, 0, 0)
        self._button_layout.setSpacing(8)
        self._button_layout.addStretch()
        layout.addWidget(self._button_container)
        self._button_container.hide()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if self._back.isVisible():
            self._back.dock_under(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._back.isVisible():
            self._back.dock_under(self)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        painter.fillPath(path, _BG)

    # --- act mode ---------------------------------------------------------

    def show_checklist(self, act: int, steps, pointer: int, progress, off_route: bool) -> None:
        """The whole act as a checklist: done steps ticked and collapsed, the
        current step expanded into bullets, upcoming steps collapsed."""
        self._button_container.hide()
        self._zone_label.hide()
        self._steps_label.show()

        self._act_label.setText(header_text(act, off_route))
        self._act_label.setStyleSheet(
            f"color: {OFF_ROUTE_COLOR if off_route else _ACT_COLOR}; background: transparent;"
        )
        self._progress_label.setText(progress_text(progress))
        self._progress_label.show()
        # The checklist is HTML so each line can carry its own colour; map mode
        # feeds this same label plain text, so the format has to be explicit.
        self._steps_label.setTextFormat(Qt.TextFormat.RichText)
        self._steps_label.setText(checklist_html(steps, pointer))

        self._set_interactive(False)
        self.adjustSize()
        self._snap_top_left()
        self.show()
        self._back.dock_under(self)
        self._back.show()

    def show_campaign_complete(self) -> None:
        self._back.hide()
        self.show_status("Campaign complete.\nKitava is dead — go map.")

    # --- map mode ---------------------------------------------------------

    def _reset_chrome(self) -> None:
        """Undo anything the checklist view set up."""
        self._progress_label.hide()
        self._zone_label.show()
        self._steps_label.setTextFormat(Qt.TextFormat.PlainText)
        self._act_label.setStyleSheet(f"color: {_ACT_COLOR}; background: transparent;")
        self._back.hide()

    def show_status(self, message: str) -> None:
        """Show a plain status message (startup / waiting), so the overlay is
        visible immediately and the player knows it's running."""
        self._reset_chrome()
        self._button_container.hide()
        self._steps_label.hide()
        self._act_label.setText("PoE Campaign Overlay")
        self._zone_label.setText(message)
        self._set_interactive(False)
        self.adjustSize()
        self._snap_top_left()
        self.show()

    def show_zone(self, zone_name: str, steps: list[str], act: int) -> None:
        self._reset_chrome()
        self._button_container.hide()
        self._steps_label.show()
        self._act_label.setText(f"Act {act}" if act > 0 else "")
        self._zone_label.setText(f"◆  {zone_name}")
        self._steps_label.setText("\n".join(f"  • {s}" for s in steps))
        self._set_interactive(False)
        self.adjustSize()
        self._snap_top_left()
        self.show()

    def show_act_selection(self, zone_name: str, possible_acts: list[int]) -> None:
        self._reset_chrome()
        self._steps_label.hide()
        self._act_label.setText("Which act are you in?")
        self._zone_label.setText(f"◆  {zone_name}")

        # Rebuild buttons for this selection
        while self._button_layout.count() > 1:  # keep the trailing stretch
            item = self._button_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for act in possible_acts:
            btn = QPushButton(f"Act {act}")
            btn.setStyleSheet(_BTN_STYLE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, a=act: self.act_selected.emit(a))
            self._button_layout.insertWidget(self._button_layout.count() - 1, btn)

        self._button_container.show()
        self._set_interactive(True)
        self.adjustSize()
        self._snap_top_left()
        self.show()

    def show_no_data(self, zone_name: str) -> None:
        """Show the zone with a 'no data' note instead of hiding the overlay."""
        self._reset_chrome()
        self._button_container.hide()
        self._steps_label.show()
        self._act_label.setText("")
        self._zone_label.setText(f"◆  {zone_name}")
        self._steps_label.setText("  • No data for this zone")
        self._set_interactive(False)
        self.adjustSize()
        self._snap_top_left()
        self.show()

    def _set_interactive(self, interactive: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, not interactive)

    def _snap_top_left(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.left() + _MARGIN, screen.top() + _MARGIN)
