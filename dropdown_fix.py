from PyQt6.QtCore import QPoint, QTimer
from PyQt6.QtWidgets import QApplication, QComboBox


_original_show_popup = QComboBox.showPopup


def _position_popup_below(combo):
    """Keep every combo popup below its control and within the screen."""
    popup = combo.view().window()
    if not popup.isVisible():
        return

    anchor = combo.mapToGlobal(QPoint(0, combo.height()))
    screen = QApplication.screenAt(anchor) or combo.screen()
    if screen is None:
        return
    available = screen.availableGeometry()

    width = min(max(combo.width(), popup.width()), available.width())
    x = min(max(anchor.x(), available.left()),
            available.right() - width + 1)
    space_below = available.bottom() - anchor.y() + 1
    if space_below <= 0:
        return

    height = min(popup.height(), space_below)
    popup.setGeometry(x, anchor.y(), width, height)


def _show_popup_below(combo):
    _original_show_popup(combo)
    # Qt lays out the popup after showPopup returns, so position it next turn.
    QTimer.singleShot(0, lambda: _position_popup_below(combo))


def install_dropdown_popup_fix():
    """Position all QComboBox popups below their buttons."""
    QComboBox.showPopup = _show_popup_below
