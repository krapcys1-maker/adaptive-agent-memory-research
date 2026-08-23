"""Guard against tests that exist but never run.

Six test methods in this suite were once appended after a module's
``if __name__ == "__main__":`` block. Because that guard's body is indented the
same as a class body, Python parsed them as part of the guard: they were valid
code, they were never collected, and a commit message claimed one of them pinned
an invariant it had never once checked.

Nothing caught it. The suite stayed green because a test that does not run
cannot fail, and the total only moved by the number that vanished.

This module makes that class of mistake loud. It parses every test file and
asserts that each ``test_*`` function is reachable by pytest — defined at module
level or directly in a class body, never nested inside a conditional, a loop, a
``try``, or another function.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
TEST_FILES = sorted(path for path in TESTS.glob("test_*.py") if path.name != Path(__file__).name)

# Nodes that pytest cannot see through. A test defined inside any of these is
# either never executed or executed only under a condition pytest does not meet.
OPAQUE = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.FunctionDef, ast.AsyncFunctionDef)


def unreachable_tests(source: str) -> list[tuple[str, int, str]]:
    """Every test function pytest cannot collect, with the construct hiding it."""
    tree = ast.parse(source)
    found: list[tuple[str, int, str]] = []

    def walk(node: ast.AST, blockers: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            name = getattr(child, "name", "")
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and name.startswith("test_"):
                if blockers:
                    found.append((name, child.lineno, blockers[-1]))
                # A nested helper inside a test is not itself a test; stop here.
                continue
            if isinstance(child, ast.ClassDef):
                walk(child, blockers)
            elif isinstance(child, OPAQUE):
                label = type(child).__name__
                if isinstance(child, ast.If):
                    label = "if __name__ guard" if _is_main_guard(child) else "if"
                walk(child, blockers + [label])
            else:
                walk(child, blockers)

    walk(tree, [])
    return found


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
    )


@pytest.mark.parametrize("path", TEST_FILES, ids=[p.name for p in TEST_FILES])
def test_every_test_function_is_reachable(path: Path) -> None:
    hidden = unreachable_tests(path.read_text(encoding="utf-8"))
    assert not hidden, "\n".join(
        f"{path.name}:{line} {name} is unreachable, nested inside {blocker}"
        for name, line, blocker in hidden
    )


def test_the_guard_detects_a_test_hidden_in_a_main_block() -> None:
    """The failure that actually happened, as a fixture."""
    source = (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_visible(self): pass\n"
        'if __name__ == "__main__":\n'
        "    unittest.main()\n"
        "    def test_swallowed(self): pass\n"
    )
    hidden = unreachable_tests(source)
    assert [name for name, _, _ in hidden] == ["test_swallowed"]
    assert hidden[0][2] == "if __name__ guard"


def test_the_guard_accepts_ordinary_placements() -> None:
    source = (
        "import unittest\n"
        "def test_module_level(): pass\n"
        "class T(unittest.TestCase):\n"
        "    def test_in_class(self): pass\n"
        'if __name__ == "__main__":\n'
        "    unittest.main()\n"
    )
    assert unreachable_tests(source) == []


def test_a_helper_nested_inside_a_test_is_not_flagged() -> None:
    source = (
        "def test_outer():\n"
        "    def test_helper_not_collected_by_pytest_anyway(): pass\n"
        "    test_helper_not_collected_by_pytest_anyway()\n"
    )
    assert unreachable_tests(source) == []
