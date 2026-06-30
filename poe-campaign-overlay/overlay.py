from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor, QPainterPath

_WIDTH = 360
_MARGIN = 16
_PADDING = 12
_BG = QColor(10, 10, 10, 210)
_ZONE_COLOR = "#e8c97a"
_STEP_COLOR = "#cccccc"
_ACT_COLOR = "#888888"


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._build_window()
        self._build_ui()

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

        self._act_label = QLabel()
        self._act_label.setFont(QFont("Consolas", 9))
        self._act_label.setStyleSheet(f"color: {_ACT_COLOR}; background: transparent;")
        layout.addWidget(self._act_label)

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

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        painter.fillPath(path, _BG)

    def show_zone(self, zone_name: str, steps: list[str], act: int) -> None:
        self._act_label.setText(f"Act {act}" if act > 0 else "")
        self._zone_label.setText(f"◆  {zone_name}")
        self._steps_label.setText("\n".join(f"  • {s}" for s in steps))
        self.adjustSize()
        self._snap_top_right()
        self.show()

    def hide_zone(self) -> None:
        self.hide()

    def _snap_top_right(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - _MARGIN, screen.top() + _MARGIN)
