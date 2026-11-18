
import csv
import json
import math
import re
import sqlite3
import sys
from dataclasses import *
from pathlib import *

from constants import *

def application_directory():

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent
separators = re.compile(points_separators)

column_count = 2

class PointsFileError(ValueError):
    pass
def _parse_line(text):
    parts = separators.split(text)
    if len(parts) != column_count:
        raise ValueError
    x, y = float(parts[0]), float(parts[1])
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError
    return [x, y]
def read_points(path):
    points = []

    header_allowed = True

    with open(path, encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            text = line.strip()

            if not text:
                continue

            try:
                points.append(_parse_line(text))

            except ValueError:
                if not header_allowed:
                    raise PointsFileError(
                        f"строка {line_number}: ожидались два числа "
                        "(дробная часть через точку)") from None

            header_allowed = False

    if not points:
        raise PointsFileError(
            "в файле нет точек (дробная часть пишется через точку)")
    return points

graph_format_name = "graph_builder_graph"

def write_points(path, points, delimiter=","):
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=delimiter)
        writer.writerow(("x", "y"))
        writer.writerows(points)

def _validated_points(raw_points):
    if not isinstance(raw_points, list):
        raise ValueError("список точек должен быть массивом")
    points = []
    for number, point in enumerate(raw_points, start=1):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"точка {number}: нужны две координаты")
        try:
            x, y = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            raise ValueError(f"точка {number}: координаты должны быть числами") from None
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"точка {number}: координаты должны быть конечными числами")
        points.append([x, y])
    return points

def write_graph(path, graph, name=""):
    data = {
        "format": graph_format_name,
        "name": str(name),
        "graph": {
            "mode": graph.mode,
            "degree": int(graph.degree),
            "equation": graph.equation,
            "color": graph.color,
            "points": _validated_points(graph.points),
        },
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)

def read_graph(path):
    try:
        with open(path, encoding="utf-8-sig") as file:
            data = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"не удалось разобрать файл графика: {error}") from None
    if not isinstance(data, dict) or data.get("format") != graph_format_name:
        raise ValueError("это не файл графика Graph Builder")
    graph = data.get("graph")
    if not isinstance(graph, dict):
        raise ValueError("в файле отсутствуют данные графика")
    mode = graph.get("mode")
    if mode not in modes:
        raise ValueError("неизвестный метод построения графика")
    try:
        degree = int(graph.get("degree"))
    except (TypeError, ValueError):
        raise ValueError("неверная степень полинома") from None
    if not min_exponent <= degree <= max_exponent:
        raise ValueError(f"степень должна быть от {min_exponent} до {max_exponent}")
    equation = graph.get("equation", "")
    color = graph.get("color", "#1565c0")
    if not isinstance(equation, str) or not isinstance(color, str) or not color:
        raise ValueError("неверные параметры уравнения или цвета")
    return {
        "name": str(data.get("name") or "Импортированный график"),
        "mode": mode, "degree": degree, "equation": equation,
        "color": color, "points": _validated_points(graph.get("points", [])),
    }

@dataclass
class GraphSummary:
    id: int
    name: str
    mode: str
    points_count: int
    equation: str


@dataclass
class SavedGraph:
    id: int
    name: str
    mode: str
    degree: int
    equation: str
    color: str
    points: list


class Database:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._prepare_schema()

    def _prepare_schema(self):
        with self.connection:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS graphs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "name TEXT NOT NULL UNIQUE, "
                "mode TEXT NOT NULL, "
                "degree INTEGER NOT NULL DEFAULT 3, "
                "equation TEXT NOT NULL DEFAULT '', "
                "color TEXT NOT NULL DEFAULT '#1565c0')"
            )
            columns = {row[1] for row in self.connection.execute(
                "PRAGMA table_info(graphs)").fetchall()}
            additions = {
                "degree": "INTEGER NOT NULL DEFAULT 3",
                "equation": "TEXT NOT NULL DEFAULT ''",
                "color": "TEXT NOT NULL DEFAULT '#1565c0'",
            }
            for column, definition in additions.items():
                if column not in columns:
                    self.connection.execute(
                        f"ALTER TABLE graphs ADD COLUMN {column} {definition}")
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS points ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "graph_id INTEGER NOT NULL REFERENCES graphs(id) ON DELETE CASCADE, "
                "x REAL NOT NULL, y REAL NOT NULL)"
            )

    @staticmethod
    def _normalize_mode(mode):
        aliases = {
            "Кубический сплайн": "Сплайн",
            "Линейная интерполяция": "Линейная",
            "Полиномиальная": "Полином",
        }
        return aliases.get(mode, mode)

    def close(self):
        self.connection.close()

    def find_id(self, name):
        row = self.connection.execute(
            "SELECT id FROM graphs WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None

    def save_graph(self, name, mode, points, degree=default_exponent,
                   equation="", color="#1565c0"):
        validated = _validated_points(points)
        if mode not in modes:
            raise ValueError("неизвестный метод построения графика")
        degree = int(degree)
        if not min_exponent <= degree <= max_exponent:
            raise ValueError("неверная степень полинома")
        if not isinstance(equation, str) or not isinstance(color, str) or not color:
            raise ValueError("неверные параметры графика")
        if not validated and not equation.strip():
            raise ValueError("нельзя сохранить пустой график")
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO graphs (name, mode, degree, equation, color) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, mode, degree, equation, color))
            graph_id = cursor.lastrowid
            self._insert_points(graph_id, validated)
        return graph_id

    def _insert_points(self, graph_id, points):
        self.connection.executemany(
            "INSERT INTO points (graph_id, x, y) VALUES (?, ?, ?)",
            [(graph_id, x, y) for x, y in points])

    def list_graphs(self):
        rows = self.connection.execute(
            "SELECT g.id, g.name, g.mode, COUNT(p.id), g.equation "
            "FROM graphs g LEFT JOIN points p ON p.graph_id = g.id "
            "GROUP BY g.id ORDER BY g.id DESC").fetchall()
        return [GraphSummary(*row) for row in rows]

    def load_graph(self, graph_id):
        row = self.connection.execute(
            "SELECT id, name, mode, degree, equation, color "
            "FROM graphs WHERE id = ?", (graph_id,)).fetchone()
        if row is None:
            return None
        return SavedGraph(*row, points=self.get_points(graph_id))

    def get_points(self, graph_id):
        rows = self.connection.execute(
            "SELECT x, y FROM points WHERE graph_id = ? ORDER BY id",
            (graph_id,)).fetchall()
        return [[x, y] for x, y in rows]

    def replace_points(self, graph_id, points):
        validated = _validated_points(points)
        with self.connection:
            self.connection.execute(
                "DELETE FROM points WHERE graph_id = ?", (graph_id,))
            self._insert_points(graph_id, validated)

    def rename_graph(self, graph_id, name):
        with self.connection:
            self.connection.execute(
                "UPDATE graphs SET name = ? WHERE id = ?", (name, graph_id))

    def delete_graph(self, graph_id):
        with self.connection:
            self.connection.execute(
                "DELETE FROM graphs WHERE id = ?", (graph_id,))
