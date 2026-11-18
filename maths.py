
import ast
import math
import re
import warnings
from dataclasses import *
from typing import *
import numpy as np
from constants import *

variable_name = "x"

known_constants = {"pi": math.pi, "e": math.e}

functions = {
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "tg": np.tan,

    "cot": lambda x: 1 / np.tan(x),
    "ctg": lambda x: 1 / np.tan(x),
    "ln": np.log,
    "log": np.log,
    "log2": np.log2,
    "log10": np.log10,
    "abs": np.abs,
}

binary_operations = {
    ast.Add: np.add,
    ast.Sub: np.subtract,
    ast.Mult: np.multiply,
    ast.Div: np.divide,
    ast.Pow: np.power,
}

unary_operations = {ast.UAdd: np.positive, ast.USub: np.negative}

equation_prefix = re.compile(r"^\s*(y|f\s*\(\s*x\s*\))\s*=")

class EquationError(ValueError):
    pass

def _evaluate(node, x):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, x)
    if isinstance(node, ast.Constant):
        if type(node.value) in (int, float):
            return float(node.value)
        raise EquationError("недопустимое выражение")
    if isinstance(node, ast.Name):
        if node.id == variable_name:
            return x
        if node.id in known_constants:
            return known_constants[node.id]
        raise EquationError(f"неизвестное имя «{node.id}»")
    if isinstance(node, ast.BinOp) and type(node.op) in binary_operations:
        operation = binary_operations[type(node.op)]
        return operation(_evaluate(node.left, x), _evaluate(node.right, x))

    if isinstance(node, ast.UnaryOp) and type(node.op) in unary_operations:
        operation = unary_operations[type(node.op)]
        return operation(_evaluate(node.operand, x))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in functions:
            raise EquationError(f"неизвестная функция «{node.func.id}»")
        if len(node.args) != 1 or node.keywords:
            raise EquationError("функция принимает один аргумент")
        return functions[node.func.id](_evaluate(node.args[0], x))
    raise EquationError("недопустимое выражение")

def compile_equation(text):  
    text = text.replace("х", "x").replace("Х", "X").lower()

    text = equation_prefix.sub("", text).strip()
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError):
        raise EquationError("ошибка синтаксиса") from None

    with np.errstate(all="ignore"):
        _evaluate(tree, np.linspace(-1.0, 1.0, 3))

    def function(x):
        with np.errstate(all="ignore"):
            values = np.asarray(_evaluate(tree, x), dtype=float)
        return np.broadcast_to(values, np.shape(x)).copy()
    return function
superscript_digits = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
negligible_coefficient = 1e-9

@dataclass
class Curve:


    t: np.ndarray
    values: np.ndarray
    label: str
    function: Callable

    has_inflections: bool = True

def build_spline(xs, ys):

    count = len(xs)
    steps = np.diff(xs)

    matrix = np.zeros((count, count))
    right_side = np.zeros(count)

    matrix[0, 0] = matrix[-1, -1] = 1

    for i in range(1, count - 1):
        matrix[i, i - 1] = steps[i - 1]
        matrix[i, i] = 2 * (steps[i - 1] + steps[i])
        matrix[i, i + 1] = steps[i]
        slope_after = (ys[i + 1] - ys[i]) / steps[i]
        slope_before = (ys[i] - ys[i - 1]) / steps[i - 1]
        right_side[i] = 6 * (slope_after - slope_before)

    second_derivatives = np.linalg.solve(matrix, right_side)

    def spline(t):

        i = np.clip(np.searchsorted(xs, t) - 1, 0, count - 2)
        step = steps[i]
        left = xs[i + 1] - t
        right = t - xs[i]
        m_left = second_derivatives[i]
        m_right = second_derivatives[i + 1]
        return (m_left * left ** 3 / (6 * step)
                + m_right * right ** 3 / (6 * step)
                + (ys[i] / step - m_left * step / 6) * left
                + (ys[i + 1] / step - m_right * step / 6) * right)

    return spline

def format_polynomial(coefficients):

    degree = len(coefficients) - 1
    text = ""

    for index, coefficient in enumerate(coefficients):
        power = degree - index

        if abs(coefficient) < negligible_coefficient:
            continue

        value = abs(coefficient)
        if power == 0:
            term = f"{value:.4g}"
        else:

            term = "" if abs(value - 1) < negligible_coefficient \
                else f"{value:.4g}"
            term += "x"
            if power > 1:
                term += str(power).translate(superscript_digits)

        if not text:
            text = ("-" if coefficient < 0 else "") + term
        else:
            text += (" - " if coefficient < 0 else " + ") + term

    return "y = " + (text or "0")

def equation_curve(function, left, right):

    t = np.linspace(left, right, samples)
    return Curve(t, function(t), "", function)

def points_curve(points, mode, degree, left, right):

    unique = {}
    for x, y in points:
        unique[x] = y

    if len(unique) < 2:
        return None

    xs = np.array(sorted(unique))
    ys = np.array([unique[x] for x in xs])
    label = f"Точек: {len(xs)}"

    if mode == m_beskonechnaya:
        degree = min(degree, len(xs) - 1)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            coefficients = np.polyfit(xs, ys, degree)

        def polynomial(x):
            return np.polyval(coefficients, x)

        t = np.linspace(left, right, samples)
        return Curve(t, polynomial(t), format_polynomial(coefficients),
                     polynomial)

    low = max(xs[0], left)
    high = min(xs[-1], right)
    if low >= high:
        return None
    t = np.linspace(low, high, samples)

    if mode == m_linear:

        def polyline(x):
            return np.interp(x, xs, ys)

        return Curve(t, polyline(t), label, polyline, has_inflections=False)

    spline = build_spline(xs, ys)
    return Curve(t, spline(t), label, spline)

@dataclass
class AnalysisResult:

    maxima: list = field(default_factory=list)
    minima: list = field(default_factory=list)
    inflections: list = field(default_factory=list)

def find_runs(values, jump_limit):

    with np.errstate(all="ignore"):
        finite = np.isfinite(values)
        linked = finite[:-1] & finite[1:]
        linked &= np.abs(np.diff(values)) <= jump_limit

    starts = np.flatnonzero(np.concatenate(([True], ~linked)))
    ends = np.append(starts[1:], len(values))
    runs = []

    for start, end in zip(starts, ends):
        if end - start >= min_length and finite[start]:
            runs.append((int(start), int(end)))
    return runs

def sign_flips(values, tolerance):

    signs = np.where(np.abs(values) > tolerance, np.sign(values), 0.0)

    nonzero = np.flatnonzero(signs)
    if len(nonzero) < 2:
        empty_indexes = np.array([], dtype=int)
        return empty_indexes, empty_indexes, np.array([])
    kept = signs[nonzero]

    flips = np.flatnonzero(kept[1:] != kept[:-1])

    return nonzero[flips], nonzero[flips + 1], kept[flips]

def refine_extremum(function, low, high, find_maximum):

    direction = 1.0 if find_maximum else -1.0

    for _ in range(search_iterations):
        third = (high - low) / 3
        left = low + third
        right = high - third
        move_right = direction * function(left) < direction * function(right)

        low = np.where(move_right, left, low)
        high = np.where(move_right, high, right)
    x = (low + high) / 2
    return x, function(x)

def bisect_root(function, low, high, signs):

    for _ in range(search_iterations):
        middle = (low + high) / 2
        same_sign = np.sign(function(middle)) == signs
        low = np.where(same_sign, middle, low)
        high = np.where(same_sign, high, middle)
    return (low + high) / 2

def analyze_curve(curve, runs):

    t = curve.t
    function = curve.function
    step = t[1] - t[0]
    result = AnalysisResult()
    with np.errstate(all="ignore"):
        for start, end in runs:
            run_t = t[start:end]
            run_values = curve.values[start:end]

            magnitude = 1 + np.max(np.abs(run_values))

            slope = np.diff(run_values) / step
            before, after, signs = sign_flips(
                slope, dopusk * magnitude / step)

            for find_maximum, found in ((True, result.maxima),
                                        (False, result.minima)):
                chosen = (signs > 0) == find_maximum
                x, value = refine_extremum(
                    function, run_t[before[chosen]],
                    run_t[after[chosen] + 1], find_maximum)
                found.extend(zip(x.tolist(), value.tolist()))

            if not curve.has_inflections:
                continue

            curvature = np.diff(run_values, 2) / step ** 2
            before, after, signs = sign_flips(
                curvature, dopusk * magnitude / step ** 2)

            half_step = step / 2

            def second_difference(x):

                return (function(x + half_step) - 2 * function(x)
                        + function(x - half_step))

            x = bisect_root(second_difference, run_t[before + 1],
                            run_t[after + 1], signs)
            result.inflections.extend(zip(x.tolist(), function(x).tolist()))

    result.maxima = sorted(result.maxima)[:max_markers]
    result.minima = sorted(result.minima)[:max_markers]
    result.inflections = sorted(result.inflections)[:max_markers]
    return result

def find_intersections(first, second, jump_limit):

    low = max(first.t[0], second.t[0])
    high = min(first.t[-1], second.t[-1])
    if low >= high:
        return []

    def difference(x):

        return first.function(x) - second.function(x)

    t = np.linspace(low, high, samples)
    values = difference(t)
    points = []
    with np.errstate(all="ignore"):
        for start, end in find_runs(values, 2 * jump_limit):
            run_t = t[start:end]
            run_values = values[start:end]

            tolerance = dopusk * (1 + np.max(np.abs(run_values)))
            before, after, signs = sign_flips(run_values, tolerance)

            x = bisect_root(difference, run_t[before], run_t[after],
                            signs)
            points.extend(zip(x.tolist(), first.function(x).tolist()))
    return sorted(points)[:max_markers]
