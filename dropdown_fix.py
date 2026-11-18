from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QStyle, QStyleOptionComboBox


_original_show_popup = QComboBox.showPopup
_original_mouse_press = QComboBox.mousePressEvent
_original_mouse_release = QComboBox.mouseReleaseEvent


def _clicked_arrow(combo, event):
    option = QStyleOptionComboBox()
    combo.initStyleOption(option)
    hit = combo.style().hitTestComplexControl(
        QStyle.ComplexControl.CC_ComboBox,
        option,
        event.position().toPoint(),
        combo,
    )
    return hit == QStyle.SubControl.SC_ComboBoxArrow


def _button_only_mouse_press(combo, event):
    # The popup is intentionally opened only by the drop-down arrow button.
    if event.button() == Qt.MouseButton.LeftButton and not _clicked_arrow(combo, event):
        combo.setFocus(Qt.FocusReason.MouseFocusReason)
        event.accept()
        return
    _original_mouse_press(combo, event)


def _button_only_mouse_release(combo, event):
    if event.button() == Qt.MouseButton.LeftButton and not _clicked_arrow(combo, event):
        event.accept()
        return
    _original_mouse_release(combo, event)


def _style_and_position_popup(combo):
    view = combo.view()
    popup = view.window()
    if not popup.isVisible():
        return

    # Remove native frame/viewport edges that otherwise show up as white lines.
    view.setFrameShape(view.Shape.NoFrame)
    view.setLineWidth(0)
    view.setStyleSheet("""
        QAbstractItemView {
            background-color: #1b2938;
            color: #e5edf5;
            border: none;
            outline: none;
            padding: 3px;
            selection-background-color: #28658d;
            selection-color: #ffffff;
        }
        QAbstractItemView::item {
            min-height: 28px;
            padding: 5px 9px;
            border: none;
            border-radius: 4px;
        }
        QAbstractItemView::item:hover {
            background-color: #243f57;
            color: #ffffff;
        }
    """)
    popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    popup.setStyleSheet("""
        background-color: #1b2938;
        color: #e5edf5;
        border: 1px solid #40566d;
        border-radius: 7px;
    """)

    anchor = combo.mapToGlobal(QPoint(0, combo.height() + 2))
    screen = QApplication.screenAt(anchor) or combo.screen()
    if screen is None:
        return
    available = screen.availableGeometry()
    width = min(max(combo.width(), popup.width()), available.width())
    x = min(max(anchor.x(), available.left()), available.right() - width + 1)
    space_below = available.bottom() - anchor.y() + 1
    if space_below <= 0:
        return

    height = min(popup.height(), space_below)
    popup.setGeometry(x, anchor.y(), width, height)


def _show_popup_below(combo):
    _original_show_popup(combo)
    # Qt finishes native popup layout after showPopup returns.
    QTimer.singleShot(0, lambda: _style_and_position_popup(combo))


def install_dropdown_popup_fix():
    """Use arrow-button-only activation and style/position native combo popups."""
    QComboBox.showPopup = _show_popup_below
    QComboBox.mousePressEvent = _button_only_mouse_press
    QComboBox.mouseReleaseEvent = _button_only_mouse_release
