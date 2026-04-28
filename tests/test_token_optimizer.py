"""Tests for engine/token_optimizer.py."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from engine.token_optimizer import (
    TokenOptimizer,
    apply_diff_patch,
    get_code_skeleton,
    prune_terminal_output,
    estimate_tokens,
)


# ---------------------------------------------------------------------------
# prune_terminal_output
# ---------------------------------------------------------------------------


def test_prune_short_output_unchanged() -> None:
    """Outputs within the limit should be returned unchanged."""
    raw = "\n".join(f"line {i}" for i in range(20))
    result = prune_terminal_output(raw, max_head=50, max_tail=50)
    assert result == raw


def test_prune_long_output_contains_notice() -> None:
    """Long outputs should contain the pruning notice."""
    raw = "\n".join(f"line {i}" for i in range(300))
    result = prune_terminal_output(raw, max_head=50, max_tail=50)
    assert "pruned" in result
    assert "line 0" in result
    assert "line 299" in result


def test_prune_preserves_first_and_last_lines() -> None:
    raw_lines = [f"L{i}" for i in range(200)]
    raw = "\n".join(raw_lines)
    result = prune_terminal_output(raw, max_head=10, max_tail=10)
    assert "L0" in result
    assert "L9" in result
    assert "L190" in result
    assert "L199" in result
    # Middle should not appear
    assert "L100" not in result


def test_prune_exact_threshold_not_pruned() -> None:
    """Output at exactly head+tail lines should NOT be pruned."""
    raw = "\n".join(f"x{i}" for i in range(6))
    result = prune_terminal_output(raw, max_head=3, max_tail=3)
    assert "pruned" not in result


# ---------------------------------------------------------------------------
# apply_diff_patch
# ---------------------------------------------------------------------------


def test_apply_diff_patch_success(tmp_path: Path) -> None:
    target = tmp_path / "test.py"
    target.write_text("def old():\n    return 1\n")
    success = apply_diff_patch(str(target), "def old():", "def new():")
    assert success is True
    assert "def new():" in target.read_text()


def test_apply_diff_patch_not_found(tmp_path: Path) -> None:
    target = tmp_path / "test.py"
    target.write_text("def something():\n    pass\n")
    success = apply_diff_patch(str(target), "def nonexistent():", "def other():")
    assert success is False
    assert "def something():" in target.read_text()  # unchanged


def test_apply_diff_patch_file_not_found() -> None:
    success = apply_diff_patch("/nonexistent/path/file.py", "old", "new")
    assert success is False


def test_apply_diff_patch_replaces_first_only(tmp_path: Path) -> None:
    target = tmp_path / "dup.py"
    target.write_text("x = 1\nx = 1\n")
    apply_diff_patch(str(target), "x = 1", "x = 2")
    content = target.read_text()
    assert content.count("x = 2") == 1
    assert content.count("x = 1") == 1


# ---------------------------------------------------------------------------
# get_code_skeleton
# ---------------------------------------------------------------------------


_SAMPLE_SOURCE = textwrap.dedent("""
    class Foo:
        \"\"\"A sample class.\"\"\"

        def __init__(self, x: int) -> None:
            \"\"\"Initialise Foo.\"\"\"
            self.x = x

        def double(self) -> int:
            return self.x * 2

    async def async_helper(name: str, count: int = 5) -> list[str]:
        \"\"\"Async utility.\"\"\"
        return [name] * count

    def simple(a, b):
        return a + b
""")


def test_get_code_skeleton_file_not_found() -> None:
    result = get_code_skeleton("/nonexistent/file.py")
    assert "ERROR" in result


def test_get_code_skeleton_parses_class(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text(_SAMPLE_SOURCE)
    skeleton = get_code_skeleton(str(src))
    assert "class Foo" in skeleton
    assert "def __init__" in skeleton
    assert "def double" in skeleton
    # Implementation should NOT be present
    assert "self.x * 2" not in skeleton
    assert "return [name] * count" not in skeleton


def test_get_code_skeleton_parses_async_function(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text(_SAMPLE_SOURCE)
    skeleton = get_code_skeleton(str(src))
    assert "async def async_helper" in skeleton
    assert "list[str]" in skeleton


def test_get_code_skeleton_is_valid_python(tmp_path: Path) -> None:
    """The skeleton output should be parseable Python (with ...) ."""
    src = tmp_path / "sample.py"
    src.write_text(_SAMPLE_SOURCE)
    skeleton = get_code_skeleton(str(src))
    try:
        ast.parse(skeleton)
    except SyntaxError as exc:
        pytest.fail(f"Skeleton is not valid Python: {exc}\n---\n{skeleton}")


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


def test_estimate_tokens_basic() -> None:
    assert estimate_tokens("abcd") == 1  # 4 chars = 1 token
    assert estimate_tokens("a" * 400) == 100


def test_estimate_tokens_minimum_one() -> None:
    assert estimate_tokens("") == 1
    assert estimate_tokens("x") == 1


# ---------------------------------------------------------------------------
# TokenOptimizer facade
# ---------------------------------------------------------------------------


def test_token_optimizer_facade(tmp_path: Path) -> None:
    opt = TokenOptimizer(max_head=5, max_tail=5)
    target = tmp_path / "f.txt"
    target.write_text("hello world")

    assert opt.apply_diff_patch(str(target), "hello", "goodbye") is True
    assert target.read_text() == "goodbye world"

    long_text = "\n".join(str(i) for i in range(100))
    pruned = opt.prune_terminal_output(long_text)
    assert "pruned" in pruned
