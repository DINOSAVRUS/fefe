import sys

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPalette, QColor, QFont

from constants import *
from interface import *
from storage import *

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    down_arrow = str(resource_path("arrow_down.svg")).replace("\\", "/")
    up_arrow = str(resource_path("arrow_up.svg")).replace("\\", "/")
    check_icon = str(resource_path("check.svg")).replace("\\", "/")
    app.setStyleSheet("""
        QWidget {
            color: #e5edf5;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        QMainWindow > QWidget, QDialog > QWidget {
            background-color: #151f2b;
        }
        QLabel {
            background-color: transparent;
        }
        QMainWindow, QDialog {
            background-color: #111923;
        }
        QMenuBar {
            background-color: #182432;
            color: #e5edf5;
            padding: 5px 8px;
            border-bottom: 1px solid #2b3a4b;
        }
        QMenuBar::item {
            background: transparent;
            padding: 7px 12px;
            border-radius: 6px;
        }
        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #263b50;
        }
        QMenu {
            background-color: #1b2938;
            color: #e5edf5;
            border: 1px solid #34485d;
            border-radius: 9px;
            padding: 5px;
        }
        QMenu::item {
            padding: 7px 28px 7px 12px;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #243548;
            color: #edf4fb;
            border: 1px solid #3b536b;
            border-radius: 8px;
            padding: 8px 13px;
            min-height: 18px;
        }
        QPushButton:hover {
            background-color: #304a63;
            border-color: #5a8bb5;
        }
        QPushButton:pressed {
            background-color: #1b2a39;
        }
        QPushButton:disabled {
            color: #a5b5c6;
            background-color: #1a2531;
            border-color: #34485d;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #0f1822;
            color: #e5edf5;
            border: 1px solid #34485d;
            border-radius: 7px;
            padding: 7px 9px;
            selection-background-color: #2879ad;
            selection-color: #ffffff;
        }
        QComboBox {
            padding-right: 30px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 27px;
            background-color: #263b50;
            border-left: 1px solid #405a73;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }
        QComboBox::drop-down:hover {
            background-color: #345675;
        }
        QComboBox::down-arrow {
            image: url("@DOWN_ARROW@");
            width: 11px;
            height: 11px;
        }
        QSpinBox, QDoubleSpinBox {
            padding-right: 28px;
        }
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 22px;
            background-color: #263b50;
            border-left: 1px solid #405a73;
            border-top-right-radius: 6px;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 22px;
            background-color: #263b50;
            border-left: 1px solid #405a73;
            border-top: 1px solid #405a73;
            border-bottom-right-radius: 6px;
        }
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #345675;
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            image: url("@UP_ARROW@");
            width: 10px;
            height: 10px;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            image: url("@DOWN_ARROW@");
            width: 10px;
            height: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #1b2938;
            color: #e5edf5;
            selection-background-color: #28658d;
            selection-color: #ffffff;
            border: 1px solid #40566d;
            border-radius: 7px;
            padding: 2px;
            outline: 0;
        }
        QComboBox QAbstractItemView::item {
            min-height: 28px;
            padding: 5px 10px;
            border: none;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #28658d;
            border-radius: 4px;
        }
        /* Compact, single-frame popup for the graph-library target selector */
        QComboBox#targetGraphCombo QAbstractItemView {
            background-color: #172535;
            color: #e5edf5;
            border: 1px solid #34485d;
            border-radius: 7px;
            padding: 0px;
            outline: none;
            font-size: 14px;
        }
        QComboBox#targetGraphCombo QAbstractItemView::item {
            min-height: 28px;
            padding: 4px 9px;
            margin: 2px 3px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
        }
        QComboBox#targetGraphCombo QAbstractItemView::item:selected {
            background-color: #28658d;
            color: #ffffff;
            border-radius: 5px;
        }
        QComboBox#targetGraphCombo QAbstractItemView::item:hover {
            background-color: #243f57;
            color: #ffffff;
        }
        QComboBox QAbstractItemView QScrollBar:vertical {
            background: #14202c;
            width: 9px;
            margin: 1px;
        }
        QComboBox QAbstractItemView QScrollBar::handle:vertical {
            background: #40566d;
            min-height: 20px;
            border-radius: 4px;
        }
        QComboBox QAbstractItemView QScrollBar:horizontal {
            height: 0px;
            border: none;
        }
        QGroupBox {
            background-color: #192532;
            border: 1px solid #34485d;
            border-radius: 11px;
            margin-top: 13px;
            padding: 15px 10px 10px 10px;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #8fc7ee;
        }
        QCheckBox, QRadioButton {
            spacing: 8px;
            background: transparent;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            background-color: #0f1822;
            border: 1px solid #60758a;
            border-radius: 4px;
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border: 1px solid #65b9ed;
        }
        QCheckBox::indicator:checked {
            background-color: #2879ad;
            border: 1px solid #65b9ed;
            image: url("@CHECK_ICON@");
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            background-color: #0f1822;
            border: 1px solid #60758a;
            border-radius: 8px;
        }
        QRadioButton::indicator:checked {
            width: 16px;
            height: 16px;
            background-color: #4aa6d8;
            border: 4px solid #1b2938;
            border-radius: 8px;
        }
        QListWidget, QTextEdit, QTableWidget, QTableView {
            background-color: #0f1822;
            alternate-background-color: #172331;
            color: #e5edf5;
            border: 1px solid #34485d;
            border-radius: 9px;
            padding: 5px;
            selection-background-color: #245d83;
            selection-color: #ffffff;
            outline: 0;
        }
        QListWidget::item {
            padding: 8px 10px;
            border-radius: 6px;
            margin: 2px;
        }
        QListWidget::item:selected {
            background-color: #245d83;
            color: #ffffff;
            border: 1px solid #55a9dc;
        }
        QScrollBar:vertical {
            background: #121c27;
            width: 12px;
            margin: 3px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #40566d;
            min-height: 25px;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QStatusBar {
            background-color: #182432;
            color: #aebdcb;
            border-top: 1px solid #2b3a4b;
        }
        QToolTip {
            background-color: #243548;
            color: #ffffff;
            border: 1px solid #52718e;
            padding: 5px;
            border-radius: 5px;
        }
    """.replace("@DOWN_ARROW@", down_arrow)
       .replace("@UP_ARROW@", up_arrow)
       .replace("@CHECK_ICON@", check_icon))
    database = Database(application_directory() / database_file_name)
    window = MainWindow(database)
    window.show()
    exit_code = app.exec()
    database.close()
    sys.exit(exit_code)
if __name__ == "__main__":
    main()
