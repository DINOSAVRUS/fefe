

import html
import math
from dataclasses import *

from constants import *
from maths import *

class Viewport:
    def __init__(self):
        self.center_x = 0.0
        self.center_y = 0.0
        self.scale = initial_scale
        self.width = 1
        self.height = 1

    def to_screen(self, x, y):
        return (self.width / 2 + (x - self.center_x) * self.scale,
                self.height / 2 - (y - self.center_y) * self.scale)

    def to_world(self, screen_x, screen_y):
        return (self.center_x + (screen_x - self.width / 2) / self.scale,
                self.center_y - (screen_y - self.height / 2) / self.scale)

    def pan_pixels(self, delta_x, delta_y):
        self.center_x -= delta_x / self.scale
        self.center_y += delta_y / self.scale

    def center_on(self, x, y):
        self.center_x = x
        self.center_y = y

    def zoom_at(self, screen_x, screen_y, factor):
        world_x, world_y = self.to_world(screen_x, screen_y)
        self.scale = min(max(self.scale * factor, min_scale), max_scale)
        self.center_x = world_x - (screen_x - self.width / 2) / self.scale
        self.center_y = world_y + (screen_y - self.height / 2) / self.scale

    @property
    def visible_left(self):
        return self.to_world(0, 0)[0]

    @property
    def visible_right(self):
        return self.to_world(self.width, 0)[0]

    @property
    def visible_top(self):
        return self.to_world(0, 0)[1]

    @property
    def visible_bottom(self):
        return self.to_world(0, self.height)[1]

    @property
    def view_height(self):
        return self.height / self.scale

    def grid_step(self):
        raw_step = target_pixels_grid / self.scale
        base = 10 ** math.floor(math.log10(raw_step))
        for multiplier in (1, 2, 5):
            if base * multiplier >= raw_step:
                return base * multiplier
        return base * 10
class GraphModel:
    def __init__(self, color):
        self.color = color
        self.points = []
        self.mode = default_mode
        self.degree = default_exponent
        self.equation = ""

        self.error = ""

        self._compiled_text = None
        self._compiled_function = None

    def uses_equation(self):
        return bool(self.equation.strip())

    def add_point(self, x, y):
        self.points.append([x, y])
        return len(self.points) - 1

    def move_point(self, index, x, y):
        self.points[index] = [x, y]

    def remove_point(self, index):
        del self.points[index]

    def clear(self):
        self.points = []
        self.equation = ""

    def load(self, saved):
        self.points = [list(point) for point in saved.points]
        self.mode = saved.mode
        self.equation = ""
        self.error = ""
        self._compiled_text = None
        self._compiled_function = None

    def equation_function(self):
        text = self.equation.strip()

        if text != self._compiled_text:
            self._compiled_text = text
            try:

                self._compiled_function = compile_equation(text)
                self.error = ""

            except EquationError as error:
                self._compiled_function = None
                self.error = str(error)

            except Exception:
                self._compiled_function = None
                self.error = "ошибка в уравнении"
        return self._compiled_function

    def build_curve(self, left, right):

        if self.uses_equation():
            function = self.equation_function()
            if function is None:
                return None
            return equation_curve(function, left, right)

        self.error = ""
        self._compiled_text = None
        return points_curve(self.points, self.mode, self.degree,
                            left, right)

@dataclass
class GraphResult:

    curve: Curve
    runs: list
    analysis: AnalysisResult

class GraphScene:

    def __init__(self, graphs, viewport):
        self.graphs = graphs
        self.viewport = viewport
        self.results = [None] * len(graphs)
        self.intersections = []

    def recompute(self):
        left = self.viewport.visible_left
        right = self.viewport.visible_right

        jump_limit = self.viewport.view_height
        for index, graph in enumerate(self.graphs):
            curve = graph.build_curve(left, right)
            if curve is None:
                self.results[index] = None
                continue

            runs = find_runs(curve.values, jump_limit)
            self.results[index] = GraphResult(
                curve, runs, analyze_curve(curve, runs))

        self.intersections = []
        if all(result is not None for result in self.results):
            self.intersections = find_intersections(
                self.results[0].curve, self.results[1].curve, jump_limit)

@dataclass
class AppSettings:

    graph_colors: list = field(default_factory=lambda: list(default_graphs))
    snap_by_default: bool = False
    show_maxima: bool = True
    show_minima: bool = True
    show_inflections: bool = True
    show_intersections: bool = True

def format_number(value):
    text = f"{value:.{after_point}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text

def describe_points(points):
    if not points:
        return "—"
    shown = ", ".join(f"({format_number(x)}; {format_number(y)})"
                      for x, y in points[:max_in_spisok])
    hidden = len(points) - max_in_spisok

    if hidden > 0:
        shown += f" … и ещё {hidden}"
    return shown

def _report_line(color, name, points):
    return (f'<span style="color:{color}">●</span> '
            f"{name}: {describe_points(points)}")

def report(graphs, results, intersections):
    blocks = []
    for number, (graph, result) in enumerate(zip(graphs, results), start=1):
        title = f'<b style="color:{graph.color}">График {number}</b>'

        if result is None:
            note = html.escape(graph.error) if graph.uses_equation() else ""
            blocks.append(f"<p>{title}: нет данных {note}</p>")
            continue
        analysis = result.analysis

        lines = [
            title,
            _report_line(c_max, "Максимум", analysis.maxima),
            _report_line(c_min, "Минимум", analysis.minima),
            _report_line(c_inflection, "Перегиб", analysis.inflections),
        ]
        blocks.append("<p>" + "<br>".join(lines) + "</p>")

    if all(result is not None for result in results):
        line = _report_line(c_insections, "Пересечения", intersections)
        blocks.append(f"<p>{line}</p>")
    return "".join(blocks)
