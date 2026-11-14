"""A small closed language of conditions for predictions and refutation criteria of a hypothesis ledger.

Extracted from the AAMR coordinator (``aamr_coord/lab/conditions.py``, coordinator commit c429d82); the logic is
unchanged, docstrings and error messages are translated into English. See
``docs/11-research-laboratory/hypothesis-ledger-methodology.md`` section 2.

Condition:   {"all": [c, ...]} | {"any": [c, ...]} | {"not": c} | leaf
Leaf:        {"lhs": expr, "op": "<"|"<="|">"|">="|"=="|"!=", "rhs": expr}
             shorthand: {"metric": "TrT.solved", "op": ">=", "value": expr}
Expression:  number | {"metric": name} | {"add": [e, ...]} | {"sub": [e, e]} | {"mul": [e, e]} | {"abs": e}
             shorthand: {"metric": name, "plus": k, "times": t}  ==  t * metric + k

Evaluation has three values: True, False, or None (a metric is missing). Nothing outside this dictionary is executed.
"""
from __future__ import annotations

from typing import Any

OPS = ("<", "<=", ">", ">=", "==", "!=")
_MAX_DEPTH = 12


class ConditionError(ValueError):
    pass


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _expr_metrics(e, out: set, depth: int) -> None:
    if depth > _MAX_DEPTH:
        raise ConditionError("expression too deep")
    if _is_num(e):
        return
    if not isinstance(e, dict) or len(e) == 0:
        raise ConditionError(f"invalid expression: {e!r}")
    if "metric" in e:
        if not isinstance(e["metric"], str) or not e["metric"]:
            raise ConditionError("a metric must be a non-empty name")
        extra = set(e) - {"metric", "plus", "times"}
        if extra:
            raise ConditionError(f"unknown expression fields: {sorted(extra)}")
        for k in ("plus", "times"):
            if k in e and not _is_num(e[k]):
                raise ConditionError(f"{k} must be a number")
        out.add(e["metric"])
        return
    if len(e) != 1:
        raise ConditionError(f"an expression must have exactly one operator: {sorted(e)}")
    (op, arg), = e.items()
    if op == "abs":
        _expr_metrics(arg, out, depth + 1)
    elif op in ("add", "sub", "mul"):
        if not isinstance(arg, list) or len(arg) < 2 or (op != "add" and len(arg) != 2):
            raise ConditionError(f"{op} needs a list of arguments")
        for a in arg:
            _expr_metrics(a, out, depth + 1)
    else:
        raise ConditionError(f"unknown expression operator: {op}")


def metrics_of(cond: Any, depth: int = 0) -> set[str]:
    """Validate a condition and return the names of the metrics it refers to."""
    if depth > _MAX_DEPTH:
        raise ConditionError("condition too deep")
    if not isinstance(cond, dict) or not cond:
        raise ConditionError(f"invalid condition: {cond!r}")
    out: set[str] = set()
    if "all" in cond or "any" in cond:
        if len(cond) != 1:
            raise ConditionError("all/any cannot be combined with other fields")
        items = cond.get("all", cond.get("any"))
        if not isinstance(items, list) or not items:
            raise ConditionError("all/any needs a non-empty list")
        for c in items:
            out |= metrics_of(c, depth + 1)
        return out
    if "not" in cond:
        if len(cond) != 1:
            raise ConditionError("not cannot be combined with other fields")
        return metrics_of(cond["not"], depth + 1)
    leaf = _leaf(cond)
    _expr_metrics(leaf["lhs"], out, depth + 1)
    _expr_metrics(leaf["rhs"], out, depth + 1)
    return out


def _leaf(cond: dict) -> dict:
    if "metric" in cond:
        extra = set(cond) - {"metric", "op", "value", "plus", "times"}
        if extra or "op" not in cond or "value" not in cond:
            raise ConditionError(f"a shorthand leaf needs metric/op/value: {sorted(cond)}")
        lhs = {k: cond[k] for k in ("metric", "plus", "times") if k in cond}
        leaf = {"lhs": lhs, "op": cond["op"], "rhs": cond["value"]}
    else:
        if set(cond) != {"lhs", "op", "rhs"}:
            raise ConditionError(f"a leaf needs lhs/op/rhs: {sorted(cond)}")
        leaf = cond
    if leaf["op"] not in OPS:
        raise ConditionError(f"unknown comparison operator: {leaf['op']}")
    return leaf


def _val(e, m: dict):
    if _is_num(e):
        return float(e)
    if "metric" in e:
        v = m.get(e["metric"])
        if not _is_num(v):
            return None
        return float(e.get("times", 1)) * float(v) + float(e.get("plus", 0))
    (op, arg), = e.items()
    if op == "abs":
        v = _val(arg, m)
        return None if v is None else abs(v)
    vals = [_val(a, m) for a in arg]
    if any(v is None for v in vals):
        return None
    if op == "add":
        return sum(vals)
    if op == "sub":
        return vals[0] - vals[1]
    return vals[0] * vals[1]


def _cmp(a: float, op: str, b: float) -> bool:
    eps = 1e-12
    return {"<": a < b - eps, "<=": a <= b + eps, ">": a > b + eps, ">=": a >= b - eps,
            "==": abs(a - b) <= eps, "!=": abs(a - b) > eps}[op]


def evaluate(cond: dict, m: dict) -> bool | None:
    """True, False, or None (a metric is missing). The condition must have passed ``metrics_of`` first."""
    if "all" in cond:
        vals = [evaluate(c, m) for c in cond["all"]]
        if any(v is False for v in vals):
            return False
        return None if any(v is None for v in vals) else True
    if "any" in cond:
        vals = [evaluate(c, m) for c in cond["any"]]
        if any(v is True for v in vals):
            return True
        return None if any(v is None for v in vals) else False
    if "not" in cond:
        v = evaluate(cond["not"], m)
        return None if v is None else (not v)
    leaf = _leaf(cond)
    a, b = _val(leaf["lhs"], m), _val(leaf["rhs"], m)
    if a is None or b is None:
        return None
    return _cmp(a, leaf["op"], b)
