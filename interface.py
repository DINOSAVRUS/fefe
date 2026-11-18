import math
import sqlite3
import sys
from pathlib import Path

import numpy as np
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from constants import *
from models import *
from storage import *


class CoordinateSpinBox(QDoubleSpinBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(-1_000_000_000, 1_000_000_000)
        self.setDecimals(6)
        self.setSingleStep(1.0)
        self.setFixedHeight(32)

    def textFromValue(self, value):
        if abs(value) < 0.0000005:
            return "0"
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text.replace(".", ",")

min_canvas_width = 400
min_canvas_height = 300
axis_pen_width = 2
marker_outline_width = 2
label_offset_x = 3
label_offset_y_below = 10
label_offset_y_above = 8
label_round_digits = 10
formula_font_family = "Consolas"

def resource_path(file_name):

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "resources" / file_name

def grid_lines(minimum, maximum, step):


    index = math.ceil(minimum / step)

    while index * step <= maximum:
        yield index, index * step
        index += 1

class GraphCanvas(QWidget):
    cursor_moved = pyqtSignal(float, float)

    scene_changed = pyqtSignal()

    def __init__(self, graphs, settings, parent=None):
        super().__init__(parent)

        self.graphs = graphs
        self.settings = settings

        self.viewport = Viewport()
        self.graph_scene = GraphScene(graphs, self.viewport)

        self.active_index = 0

        self.snap_to_grid = False

        self._drag_target = None

        self._panning = False
        self._last_position = None

        self.setMouseTracking(True)

        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMinimumSize(min_canvas_width, min_canvas_height)

    def refresh(self):

        self.graph_scene.recompute()
        self.update()
        self.scene_changed.emit()

    def resizeEvent(self, event):
        self.viewport.width = self.width()
        self.viewport.height = self.height()
        self.refresh()

    def _snap(self, x, y):
        if not self.snap_to_grid:
            return x, y

        unit = self.viewport.grid_step() / 2
        return round(x / unit) * unit, round(y / unit) * unit

    def _find_point(self, position):
        best = None
        best_distance = mouse_radius
        for graph in self.graphs:

            if graph.uses_equation():
                continue
            for index, (x, y) in enumerate(graph.points):

                screen_x, screen_y = self.viewport.to_screen(x, y)
                distance = math.hypot(screen_x - position.x(),
                                      screen_y - position.y())

                if distance <= best_distance:
                    best = (graph, index)
                    best_distance = distance
        return best
    def mousePressEvent(self, event):
        position = event.position()
        button = event.button()

        shift_pressed = bool(event.modifiers()
                             & Qt.KeyboardModifier.ShiftModifier)
        left = button == Qt.MouseButton.LeftButton

        if button == Qt.MouseButton.MiddleButton or (left and shift_pressed):
            self._panning = True
            self._last_position = position

        elif left:
            self._press_left(position)

        elif button == Qt.MouseButton.RightButton:
            self._remove_point(position)

    def _press_left(self, position):
        target = self._find_point(position)

        if target is None:
            graph = self.graphs[self.active_index]
            if graph.uses_equation():
                return

            x, y = self._snap(*self.viewport.to_world(position.x(),
                                                      position.y()))
            target = (graph, graph.add_point(x, y))

        self._drag_target = target
        self.refresh()

    def _remove_point(self, position):
        target = self._find_point(position)
        if target is not None:
            graph, index = target
            graph.remove_point(index)
            self.refresh()

    def mouseMoveEvent(self, event):
        position = event.position()
        x, y = self.viewport.to_world(position.x(), position.y())

        self.cursor_moved.emit(x, y)

        if self._panning:
            delta = position - self._last_position
            self._last_position = position
            self.viewport.pan_pixels(delta.x(), delta.y())
            self.refresh()

        elif self._drag_target is not None:
            graph, index = self._drag_target
            graph.move_point(index, *self._snap(x, y))
            self.refresh()

    def mouseReleaseEvent(self, event):
        self._drag_target = None
        self._panning = False

    def wheelEvent(self, event):
        position = event.position()

        zoom_in = event.angleDelta().y() > 0
        factor = zoom if zoom_in else 1 / zoom
        self.viewport.zoom_at(position.x(), position.y(), factor)
        self.refresh()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(c_background))
        self._draw_grid(painter)
        for graph, result in zip(self.graphs, self.graph_scene.results):
            if result is not None:
                self._draw_curve(painter, graph, result)
        self._draw_markers(painter)
        self._draw_points(painter)
        self._draw_formulas(painter)

    def _draw_label(self, painter, text, x, y, align_right):
        left = x - label_box_width if align_right else x
        box = QRectF(left, y - label_box_height / 2,
                     label_box_width, label_box_height)
        horizontal = (Qt.AlignmentFlag.AlignRight if align_right
                      else Qt.AlignmentFlag.AlignLeft)
        painter.drawText(box, horizontal | Qt.AlignmentFlag.AlignVCenter,
                         text)

    def _draw_grid(self, painter):
        view = self.viewport
        step = view.grid_step()
        axis_x, axis_y = view.to_screen(0, 0)

        label_x = min(max(axis_x, label_left_limit),
                      view.width - label_edge_field)
        label_y = min(max(axis_y, label_vertical_field),
                      view.height - label_vertical_field)
        grid_pen = QPen(QColor(c_grid))

        grid_pen.setCosmetic(True)
        text_pen = QPen(QColor(c_text))

        for index, value in grid_lines(view.visible_left,
                                       view.visible_right, step):
            screen_x = view.to_screen(value, 0)[0]
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(screen_x, 0),
                             QPointF(screen_x, view.height))

            if index != 0:
                painter.setPen(text_pen)
                text = f"{round(value, label_round_digits):g}"
                self._draw_label(painter, text, screen_x + label_offset_x,
                                 label_y + label_offset_y_below, False)

        for index, value in grid_lines(view.visible_bottom,
                                       view.visible_top, step):
            screen_y = view.to_screen(0, value)[1]
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(0, screen_y),
                             QPointF(view.width, screen_y))
            if index != 0:
                painter.setPen(text_pen)
                text = f"{round(value, label_round_digits):g}"
                self._draw_label(painter, text, label_x - label_offset_x - 1,
                                 screen_y - label_offset_y_above, True)

        axis_pen = QPen(QColor(c_axis), axis_pen_width)
        axis_pen.setCosmetic(True)
        painter.setPen(axis_pen)
        if 0 <= axis_x <= view.width:
            painter.drawLine(QPointF(axis_x, 0), QPointF(axis_x, view.height))
        if 0 <= axis_y <= view.height:
            painter.drawLine(QPointF(0, axis_y), QPointF(view.width, axis_y))

    def _draw_curve(self, painter, graph, result):
        pen = QPen(QColor(graph.color), line_width)
        pen.setCosmetic(True)
        painter.setPen(pen)
        curve = result.curve

        for start, end in result.runs:
            screen_x, screen_y = self.viewport.to_screen(
                curve.t[start:end], curve.values[start:end])

            screen_y = np.clip(screen_y, -screen_limit, screen_limit)

            polygon = QPolygonF([QPointF(x, y) for x, y in
                                 zip(screen_x.tolist(), screen_y.tolist())])
            painter.drawPolyline(polygon)

    def _draw_dot(self, painter, x, y, radius, color, outline_color,
                  outline_width):
        screen_x, screen_y = self.viewport.to_screen(x, y)
        painter.setPen(QPen(QColor(outline_color), outline_width))
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(screen_x, screen_y), radius, radius)

    def _draw_markers(self, painter):
        settings = self.settings
        groups = []
        if settings.show_intersections:
            groups.append((c_insections,
                           self.graph_scene.intersections))
        for result in self.graph_scene.results:
            if result is None:
                continue
            analysis = result.analysis
            if settings.show_maxima:
                groups.append((c_max, analysis.maxima))
            if settings.show_minima:
                groups.append((c_min, analysis.minima))
            if settings.show_inflections:
                groups.append((c_inflection, analysis.inflections))

        for color, points in groups:
            for x, y in points:
                self._draw_dot(painter, x, y, marker_radius, color,
                               c_background, marker_outline_width)

    def _draw_points(self, painter):

        for graph in self.graphs:
            if graph.uses_equation():
                continue
            for x, y in graph.points:
                self._draw_dot(painter, x, y, point_radius, graph.color,
                               graph.color, 1)

    def _draw_formulas(self, painter):
        font = QFont(formula_font_family, formula_font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font)
        line = 0
        for number, (graph, result) in enumerate(
                zip(self.graphs, self.graph_scene.results), start=1):
            if result is None or not result.curve.label:
                continue

            painter.setPen(QColor(graph.color))
            baseline = formula_top + formula_spase_heigth * line
            painter.drawText(QPointF(formula_left, baseline),
                             f"{number}: {result.curve.label}")
            line += 1

equation_hint = "например: sin(x) * x"

class GraphPanel(QGroupBox):


    changed = pyqtSignal()

    def __init__(self, index, model, parent=None):
        super().__init__(f"График {index + 1}", parent)

        self.model = model
        self.active_radio = QRadioButton("Ставить точки на этот график")
        self.equation_edit = QLineEdit()
        self.equation_edit.setPlaceholderText(equation_hint)
        self.mode_combo = QComboBox()
        self.mode_combo.setView(QListView())
        self.mode_combo.setMaxVisibleItems(8)
        self.mode_combo.addItems(modes)
        self.degree_spin = QSpinBox()
        self.degree_spin.setRange(min_exponent, max_exponent)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {c_errors};")

        layout = QVBoxLayout(self)
        layout.setSpacing(7)
        layout.addWidget(self.active_radio)

        equation_row = QHBoxLayout()
        equation_row.setContentsMargins(0, 0, 0, 0)
        equation_row.setSpacing(4)
        equation_label = QLabel("y =")
        equation_label.setFixedWidth(28)
        equation_row.addWidget(equation_label)
        equation_row.addWidget(self.equation_edit, 1)
        layout.addLayout(equation_row)

        method_row = QHBoxLayout()
        method_row.setContentsMargins(0, 0, 0, 0)
        method_row.setSpacing(5)
        method_row.addWidget(self.mode_combo, 1)
        method_row.addWidget(self.degree_spin)
        layout.addLayout(method_row)
        layout.addWidget(self.error_label)

        self.equation_edit.textChanged.connect(self._equation_changed)
        self.mode_combo.currentTextChanged.connect(self._mode_changed)
        self.degree_spin.valueChanged.connect(self._degree_changed)
        self.refresh_color()
        self.sync_model()

    def refresh_color(self):

        self.setStyleSheet(
            f"QGroupBox::title {{ color: {self.model.color}; }}")

    def _equation_changed(self, text):
        self.model.equation = text
        self.changed.emit()

    def _mode_changed(self, text):
        self.model.mode = text
        self.changed.emit()

    def _degree_changed(self, value):
        self.model.degree = value
        self.changed.emit()

    def sync_model(self):

        for widget in (self.equation_edit, self.mode_combo, self.degree_spin):
            widget.blockSignals(True)
        self.equation_edit.setText(self.model.equation)
        self.mode_combo.setCurrentText(self.model.mode)
        self.degree_spin.setValue(self.model.degree)
        for widget in (self.equation_edit, self.mode_combo, self.degree_spin):
            widget.blockSignals(False)
        self.show_error()

    def show_error(self):
        self.error_label.setText(self.model.error)

class PointsEditorDialog(QDialog):


    def __init__(self, points, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование точек")
        self.resize(points_editor_width, points_editor_height)

        self.points = []
        self.table = QTableWidget(0, len(points_editor_columns))
        self.table.setHorizontalHeaderLabels(points_editor_columns)

        for x, y in points:
            self._add_row(str(x), str(y))

        add_button = QPushButton("Добавить строку")
        remove_button = QPushButton("Удалить строку")

        add_button.clicked.connect(lambda: self._add_row("0", "0"))
        remove_button.clicked.connect(self._remove_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        row_buttons = QHBoxLayout()
        row_buttons.addWidget(add_button)
        row_buttons.addWidget(remove_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(row_buttons)
        layout.addWidget(buttons)

    def _add_row(self, x_text, y_text):

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(x_text))
        self.table.setItem(row, 1, QTableWidgetItem(y_text))

    def _remove_row(self):

        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def accept(self):

        points = []
        for row in range(self.table.rowCount()):

            try:
                x = float(self.table.item(row, 0).text())
                y = float(self.table.item(row, 1).text())
            except (AttributeError, ValueError):

                QMessageBox.warning(
                    self, "Ошибка",
                    f"Строка {row + 1}: нужно ввести числа "
                    "(дробная часть через точку).")
                return
            points.append([x, y])

        self.points = points
        super().accept()

id_column = 0

class LibraryWindow(QDialog):

    graph_opened = pyqtSignal(int, int, str)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.target_index = getattr(getattr(parent, "canvas", None), "active_index", 0)
        self.setWindowTitle("Библиотека графиков")
        self.resize(900, 500)
        self.setMinimumSize(850, 440)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.list_widget.setSpacing(5)
        self.list_widget.setUniformItemSizes(True)
        self.empty_label = QLabel("Библиотека пока пуста. Сохраните график сочетанием Ctrl+S.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #9ba9ba; padding: 24px;")

        self.open_button = QPushButton("Открыть")
        self.edit_button = QPushButton("Изменить точки")
        self.rename_button = QPushButton("Переименовать")
        self.delete_button = QPushButton("Удалить")
        self.open_button.setMinimumWidth(92)
        self.edit_button.setMinimumWidth(142)
        self.rename_button.setMinimumWidth(132)
        self.delete_button.setMinimumWidth(92)

        self.target_group = QButtonGroup(self)
        self.target_group.setExclusive(True)
        self.target_graph_1 = QRadioButton("График 1")
        self.target_graph_2 = QRadioButton("График 2")
        self.target_group.addButton(self.target_graph_1, 0)
        self.target_group.addButton(self.target_graph_2, 1)
        (self.target_graph_1 if self.target_index == 0 else self.target_graph_2).setChecked(True)

        self.target_graph_label = QLabel("Вставить в:")
        close_button = QPushButton("Закрыть")
        close_button.setMinimumWidth(92)
        self.target_graph_label.setMinimumWidth(76)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.delete_button)
        buttons.addSpacing(8)
        buttons.addWidget(self.target_graph_label)
        buttons.addWidget(self.target_graph_1)
        buttons.addWidget(self.target_graph_2)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.empty_label)
        layout.addLayout(buttons)

        self.list_widget.itemSelectionChanged.connect(self._selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._open_selected)
        self.open_button.clicked.connect(self._open_selected)
        self.edit_button.clicked.connect(self._edit_points)
        self.rename_button.clicked.connect(self._rename)
        self.delete_button.clicked.connect(self._delete)
        close_button.clicked.connect(self.accept)
        self.reload()

    def reload(self, selected_id=None):
        summaries = self.database.list_graphs()
        self.list_widget.clear()
        for summary in summaries:
            graph_kind = "Уравнение" if summary.equation.strip() else summary.mode
            item = QListWidgetItem(
                f"{summary.name}    ·    {graph_kind}    ·    "
                f"Точек: {summary.points_count}")
            item.setData(Qt.ItemDataRole.UserRole, summary.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, summary.name)
            item.setSizeHint(QSize(0, 58))
            self.list_widget.addItem(item)
            if summary.id == selected_id:
                self.list_widget.setCurrentItem(item)
        self.empty_label.setVisible(not summaries)
        self.list_widget.setVisible(bool(summaries))
        self._update_buttons()

    def _selected(self):
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole), item.data(Qt.ItemDataRole.UserRole + 1)

    def _selection_changed(self):
        self._update_buttons()

    def _update_buttons(self):
        enabled = self._selected() is not None
        for button in (self.open_button, self.edit_button,
                       self.rename_button, self.delete_button):
            button.setEnabled(enabled)

    def _open_selected(self, *_):
        selected = self._selected()
        if selected is None:
            return
        self.graph_opened.emit(
            selected[0], self.target_group.checkedId(), "")
        self.accept()

    def _edit_points(self):
        selected = self._selected()
        if selected is None:
            return
        graph_id = selected[0]
        dialog = PointsEditorDialog(self.database.get_points(graph_id), self)
        if dialog.exec():
            self.database.replace_points(graph_id, dialog.points)
            self.reload(graph_id)

    def _rename(self):
        selected = self._selected()
        if selected is None:
            return
        graph_id, old_name = selected
        name, accepted = QInputDialog.getText(
            self, "Переименовать график", "Название:", text=old_name)
        if not accepted:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название не может быть пустым.")
            return
        try:
            self.database.rename_graph(graph_id, name)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", "График с таким названием уже существует.")
            return
        self.reload(graph_id)

    def _delete(self):
        selected = self._selected()
        if selected is None:
            return
        answer = QMessageBox.question(
            self, "Удаление графика", f"Удалить «{selected[1]}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.database.delete_graph(selected[0])
        self.reload()

points_list_height = 90
report_caption = "Максимум, минимум и перегибы"
import_append = "append"
import_replace = "replace"

class MainWindow(QMainWindow):

    def __init__(self, database):
        super().__init__()

        self.database = database

        self.settings = AppSettings()
        self.setWindowTitle(window_title)
        self.setWindowIcon(QIcon(str(resource_path(icon_file_name))))
        self.resize(window_width, window_height)

        self.graphs = [GraphModel(color)
                       for color in self.settings.graph_colors]
        self.canvas = GraphCanvas(self.graphs, self.settings)

        self.panels = [GraphPanel(index, graph)
                       for index, graph in enumerate(self.graphs)]

        self._build_ui()
        self._build_menu()
        self._connect_signals()

        self.panels[0].active_radio.setChecked(True)
        self.snap_checkbox.setChecked(self.settings.snap_by_default)

    def _build_ui(self):

        self.snap_checkbox = QCheckBox("Привязка к сетке")
        self.clear_button = QPushButton("Очистить")
        self.point_x_spin = CoordinateSpinBox()
        self.point_y_spin = CoordinateSpinBox()
        self.point_x_spin.setValue(0)
        self.point_y_spin.setValue(0)
        self.add_point_button = QPushButton("Добавить точку")
        self.points_list = QListWidget()
        self.points_list.setMaximumHeight(points_list_height)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.status_label = QLabel()
        self.notice_label = QLabel()
        self.notice_label.setWordWrap(True)
        self.notice_label.setStyleSheet(f"color: {c_errors};")

        side_panel = QWidget()
        side_panel.setFixedWidth(side_panel_width)
        side_layout = QVBoxLayout(side_panel)
        for panel in self.panels:
            side_layout.addWidget(panel)
        side_layout.addWidget(self.snap_checkbox)
        side_layout.addWidget(self.clear_button)
        coordinate_title = QLabel("Добавить точку по координатам")
        side_layout.addWidget(coordinate_title)
        coordinate_layout = QGridLayout()
        coordinate_layout.setContentsMargins(0, 0, 0, 0)
        coordinate_layout.setHorizontalSpacing(3)
        coordinate_layout.setVerticalSpacing(2)
        coordinate_layout.setColumnMinimumWidth(0, 18)
        coordinate_layout.setColumnStretch(1, 1)
        x_label = QLabel("X")
        y_label = QLabel("Y")
        x_label.setFixedWidth(18)
        y_label.setFixedWidth(18)
        coordinate_layout.addWidget(x_label, 0, 0)
        coordinate_layout.addWidget(self.point_x_spin, 0, 1)
        coordinate_layout.addWidget(y_label, 1, 0)
        coordinate_layout.addWidget(self.point_y_spin, 1, 1)
        side_layout.addLayout(coordinate_layout)
        side_layout.addWidget(self.add_point_button)
        side_layout.addWidget(QLabel("Точки активного графика"))
        side_layout.addWidget(self.points_list)
        report_title = QLabel(report_caption)
        report_title.setWordWrap(True)
        side_layout.addWidget(report_title)
        side_layout.addWidget(self.report_view, stretch=1)
        side_layout.addWidget(self.status_label)
        side_layout.addWidget(self.notice_label)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.canvas, stretch=1)
        layout.addWidget(side_panel)
        self.setCentralWidget(central)

        self.active_group = QButtonGroup(self)
        for index, panel in enumerate(self.panels):
            self.active_group.addButton(panel.active_radio, index)

    def _build_menu(self):

        file_menu = self.menuBar().addMenu("Файл")
        self._add_action(file_menu, "Сохранить активный график", "Ctrl+S",
                         self._save_graph)
        self._add_action(file_menu, "Библиотека графиков…", "Ctrl+L",
                         self._show_library)
        file_menu.addSeparator()
        self._add_action(file_menu, "Импорт координат точек…", "Ctrl+O",
                         self._import_points)
        self._add_action(file_menu, "Импорт полного графика…", "Ctrl+Shift+O",
                         self._import_graph)
        file_menu.addSeparator()
        self._add_action(file_menu, "Экспорт координат точек…", "Ctrl+E",
                         self._export_points)
        self._add_action(file_menu, "Экспорт полного графика…", "Ctrl+Shift+E",
                         self._export_graph)

    def _add_action(self, menu, text, shortcut, handler):

        action = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(handler)
        menu.addAction(action)
        return action

    def _connect_signals(self):

        for panel in self.panels:
            panel.changed.connect(self.canvas.refresh)

        self.active_group.idClicked.connect(self._active_changed)
        self.snap_checkbox.toggled.connect(self._snap_toggled)
        self.clear_button.clicked.connect(self._clear_all)
        self.add_point_button.clicked.connect(self._add_point_from_coordinates)

        self.canvas.scene_changed.connect(self._update_panel)

        self.canvas.cursor_moved.connect(self._show_cursor)

    def _active_changed(self, index):

        self.canvas.active_index = index
        self._update_panel()

    def _snap_toggled(self, checked):

        self.canvas.snap_to_grid = checked

    def _add_point_from_coordinates(self):
        graph = self.graphs[self.canvas.active_index]
        if graph.uses_equation():
            QMessageBox.information(
                self, "Добавление точки",
                "Сначала очистите уравнение активного графика.")
            return
        graph.add_point(self.point_x_spin.value(), self.point_y_spin.value())
        self.canvas.refresh()

    def _clear_all(self):

        for graph, panel in zip(self.graphs, self.panels):
            graph.clear()
            panel.sync_model()
        self.canvas.refresh()

    def _notify(self, text):

        self.statusBar().showMessage(text, status_message_ms)

    def _save_graph(self):
        index = self.canvas.active_index
        graph = self.graphs[index]
        if not graph.points and not graph.uses_equation():
            QMessageBox.information(
                self, "Сохранение", "Сначала постройте график или добавьте точки.")
            return
        base_name = f"График {index + 1}"
        name = base_name
        suffix = 2
        while self.database.find_id(name) is not None:
            name = f"{base_name} ({suffix})"
            suffix += 1
        try:
            self.database.save_graph(
                name, graph.mode, graph.points, graph.degree,
                graph.equation, graph.color)
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(
                self, "Сохранение", f"Не удалось сохранить график: {error}")
            return
        self._notify(f"{name} сохранён в библиотеку")

    def _show_library(self):

        window = LibraryWindow(self.database, self)
        window.graph_opened.connect(self._open_graph)
        window.exec()

    def _open_graph(self, graph_id, slot, insert_mode=None):

        saved = self.database.load_graph(graph_id)
        if saved is None:
            return
        graph = self.graphs[slot]

        graph.points = [list(point) for point in saved.points]
        graph.mode = insert_mode if insert_mode in modes else saved.mode
        graph.degree = saved.degree
        graph.equation = saved.equation
        graph.color = saved.color
        graph.error = ""
        graph._compiled_text = None
        graph._compiled_function = None
        self.panels[slot].refresh_color()
        self.panels[slot].sync_model()
        self._center_points(graph)
        self.canvas.refresh()

    def _import_mode(self):

        box = QMessageBox(self)
        box.setWindowTitle("Импорт точек")
        box.setText("На графике уже есть точки.")
        replace_button = box.addButton(
            "Заменить", QMessageBox.ButtonRole.AcceptRole)
        append_button = box.addButton(
            "Добавить", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        if box.clickedButton() is replace_button:
            return import_replace
        if box.clickedButton() is append_button:
            return import_append
        return None

    def _import_points(self):

        graph = self.graphs[self.canvas.active_index]

        if graph.uses_equation():
            QMessageBox.warning(
                self, "Импорт",
                "Этот график задан уравнением. Очистите поле уравнения, "
                "чтобы загрузить точки.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт точек", "", file_filter_points)
        if not path:
            return

        try:
            points = read_points(path)
        except (OSError, PointsFileError) as error:
            QMessageBox.warning(self, "Импорт",
                                f"Не удалось прочитать файл: {error}")
            return

        mode = import_replace
        if graph.points:
            mode = self._import_mode()
            if mode is None:
                return

        if mode == import_replace:
            graph.points = points
        else:
            graph.points.extend(points)
        self._center_points(graph)
        self.canvas.refresh()
        self._notify(f"Загружено точек: {len(points)}")

    def _export_points(self):
        graph = self.graphs[self.canvas.active_index]
        if not graph.points:
            QMessageBox.information(
                self, "Экспорт координат",
                "У активного графика нет сохранённых координат точек. "
                "Если график задан уравнением, используйте экспорт полного графика.")
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Экспорт координат точек", "points.csv",
            "CSV — таблица координат (*.csv);;TXT — текстовые координаты (*.txt)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".txt" if "TXT" in selected_filter else ".csv"
        try:
            write_points(path, graph.points, delimiter="\t" if path.lower().endswith(".txt") else ",")
        except OSError as error:
            QMessageBox.warning(self, "Экспорт координат", f"Не удалось сохранить файл: {error}")
            return
        self._notify(f"Экспортировано точек: {len(graph.points)}")

    def _export_graph(self):
        index = self.canvas.active_index
        graph = self.graphs[index]
        if not graph.points and not graph.uses_equation():
            QMessageBox.information(self, "Экспорт графика", "Активный график пуст.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт полного графика", f"graph_{index + 1}.txt",
            "Текстовый файл графика (*.txt)")
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            write_graph(path, graph, name=f"График {index + 1}")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Экспорт графика", f"Не удалось сохранить файл графика: {error}")
            return
        self._notify("Полный график экспортирован")

    def _import_graph(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт полного графика", "",
            "Текстовый файл графика (*.txt)")
        if not path:
            return
        try:
            data = read_graph(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Импорт графика", f"Не удалось открыть график: {error}")
            return
        index = self.canvas.active_index
        current = self.graphs[index]
        if current.points or current.uses_equation():
            answer = QMessageBox.question(
                self, "Импорт полного графика",
                f"Заменить содержимое графика {index + 1} данными из файла?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        current.mode = data["mode"]
        current.degree = data["degree"]
        current.equation = data["equation"]
        current.color = data["color"]

        current.points = data["points"]
        current.error = ""
        current._compiled_text = None
        current._compiled_function = None
        self.panels[index].refresh_color()
        self.panels[index].sync_model()
        self._center_points(current)
        self.canvas.refresh()
        self._notify(f"Импортирован полный график: {data['name']}")

    def _center_points(self, graph):

        if graph.points:
            xs = [x for x, _ in graph.points]
            ys = [y for _, y in graph.points]
            self.canvas.viewport.center_on((min(xs) + max(xs)) / 2,
                                           (min(ys) + max(ys)) / 2)

    def _show_cursor(self, x, y):

        self.status_label.setText(
            f"x = {format_number(x)}   y = {format_number(y)}")

    def _update_panel(self):
        scene = self.canvas.graph_scene
        for panel in self.panels:
            panel.show_error()
        self.report_view.setHtml(
            report(self.graphs, scene.results,
                   scene.intersections))
        active = self.canvas.active_index
        graph = self.graphs[active]
        self.points_list.clear()
        for number, (x, y) in enumerate(sorted(graph.points), start=1):
            item = QListWidgetItem(
                f"{number:>2}.  ({format_number(x)}; {format_number(y)})")
            item.setForeground(QColor(graph.color))
            self.points_list.addItem(item)
        if graph.uses_equation():
            self.notice_label.setText(
                f"График {active + 1} задан уравнением: "
                "очистите поле ввода, чтобы ставить точки")
        else:
            self.notice_label.setText("")
