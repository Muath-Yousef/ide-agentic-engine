"""
Token Optimizer — four strategies to slash API costs:

1. prune_terminal_output  — cap verbose stdout to head+tail lines  (saves context window)
2. apply_diff_patch        — targeted str-replace instead of full rewrite  (-80% output tokens)
3. get_code_skeleton       — AST-extracted signatures only, no bodies  (-95% read tokens)
4. build_prompt_cache_blocks — Anthropic cache_control markup  (-90% input tokens on reruns)
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_HEAD_LINES: int = 50
_DEFAULT_TAIL_LINES: int = 50
_APPROX_CHARS_PER_TOKEN: int = 4  # rough Anthropic estimate


# ---------------------------------------------------------------------------
# 1. Terminal output pruning
# ---------------------------------------------------------------------------


def prune_terminal_output(
    raw: str,
    max_head: int = _DEFAULT_HEAD_LINES,
    max_tail: int = _DEFAULT_TAIL_LINES,
) -> str:
    """
    Limit terminal output to first *max_head* and last *max_tail* lines.

    Prevents context window exhaustion from verbose commands such as
    ``npm install``, ``nuclei -t ...``, or ``pip install -r requirements.txt``.
    The pruning notice instructs the agent to use ``grep`` for targeted search.
    """
    lines = raw.splitlines()
    total = len(lines)
    threshold = max_head + max_tail

    if total <= threshold:
        return raw

    pruned_count = total - threshold
    head_block = "\n".join(lines[:max_head])
    tail_block = "\n".join(lines[-max_tail:])
    notice = (
        f"\n\n[⚠️  {pruned_count} lines pruned to save tokens. "
        f"Use `grep -n 'pattern' <file>` for targeted search instead of "
        f"reading full output. Total lines: {total}]\n\n"
    )
    logger.debug("Pruned terminal output: %d → %d lines shown", total, threshold)
    return head_block + notice + tail_block


# ---------------------------------------------------------------------------
# 2. Diff / Patch editing
# ---------------------------------------------------------------------------


def apply_diff_patch(path: str, old_text: str, new_text: str) -> bool:
    """
    Apply a targeted search-and-replace to *path*.

    Returns ``False`` (and does NOT modify the file) if *old_text* is absent.
    Warns when multiple matches exist and applies only the first replacement.

    Why this saves tokens: the agent sends only the *changed* lines rather
    than rewriting a 1 000-line file, cutting output tokens by ~80 %.
    """
    target = Path(path)
    try:
        content = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("apply_diff_patch: file not found: %s", path)
        return False
    except OSError as exc:
        logger.error("apply_diff_patch: cannot read %s — %s", path, exc)
        return False

    if old_text not in content:
        logger.warning(
            "apply_diff_patch: exact match not found in %s — no changes made", path
        )
        return False

    occurrences = content.count(old_text)
    if occurrences > 1:
        logger.warning(
            "apply_diff_patch: %d matches in %s; replacing FIRST occurrence only",
            occurrences,
            path,
        )

    updated = content.replace(old_text, new_text, 1)
    target.write_text(updated, encoding="utf-8")
    logger.info("apply_diff_patch: patched %s (%d→%d chars)", path, len(content), len(updated))
    return True


# ---------------------------------------------------------------------------
# 3. AST Code Skeleton
# ---------------------------------------------------------------------------


def _format_annotation(node: ast.expr | None) -> str:
    """Render an AST annotation node as a compact string."""
    if node is None:
        return ""
    # Python 3.10+ ast.unparse is the authoritative way
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


def _format_arguments(args: ast.arguments) -> str:
    """Render function argument list as 'name: type, ...' string."""
    parts: list[str] = []

    # positional-only
    for i, arg in enumerate(args.posonlyargs):
        anno = f": {_format_annotation(arg.annotation)}" if arg.annotation else ""
        parts.append(f"{arg.arg}{anno}")
    if args.posonlyargs:
        parts.append("/")

    # regular args (with defaults aligned from the end)
    defaults_offset = len(args.args) - len(args.defaults)
    for i, arg in enumerate(args.args):
        anno = f": {_format_annotation(arg.annotation)}" if arg.annotation else ""
        default_idx = i - defaults_offset
        default = (
            f" = {_format_annotation(args.defaults[default_idx])}"
            if default_idx >= 0
            else ""
        )
        parts.append(f"{arg.arg}{anno}{default}")

    if args.vararg:
        anno = f": {_format_annotation(args.vararg.annotation)}" if args.vararg.annotation else ""
        parts.append(f"*{args.vararg.arg}{anno}")
    elif args.kwonlyargs:
        parts.append("*")

    for i, arg in enumerate(args.kwonlyargs):
        anno = f": {_format_annotation(arg.annotation)}" if arg.annotation else ""
        default = (
            f" = {_format_annotation(args.kw_defaults[i])}"
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None
            else ""
        )
        parts.append(f"{arg.arg}{anno}{default}")

    if args.kwarg:
        anno = (
            f": {_format_annotation(args.kwarg.annotation)}" if args.kwarg.annotation else ""
        )
        parts.append(f"**{args.kwarg.arg}{anno}")

    return ", ".join(parts)


def _first_docstring_line(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> str:
    """Extract the first line of a docstring, or '' if absent."""
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value.strip().splitlines()[0]
    return ""


def get_code_skeleton(path: str) -> str:
    """
    Return class and function *signatures only* — no implementation bodies.

    Gives the agent a full structural map of the file at ~5 % of the token
    cost of reading the complete source.  Includes:
      - Class declarations with their method signatures
      - Top-level function signatures
      - Type annotations and return types
      - First line of each docstring as context

    Example output::

        class MCPGateway:
            \"\"\"Central dispatcher for all tool invocations.\"\"\"
            def __init__(self, token_optimizer: Any | None = None) -> None: ...
            async def execute_batch_operations(self, request: BatchRequest) -> BatchResponse: ...

        def prune_terminal_output(raw: str, max_head: int = 50) -> str: ...
    """
    source_path = Path(path)
    if not source_path.exists():
        return f"# ERROR: file not found: {path}"

    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"# ERROR reading {path}: {exc}"

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return f"# SYNTAX ERROR in {path}: {exc}"

    lines: list[str] = [f"# Skeleton of: {path}\n"]

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append(f"class {node.name}:")
            doc = _first_docstring_line(node)
            if doc:
                lines.append(f'    """{doc}"""')

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(item, ast.AsyncFunctionDef) else "def"
                    sig_args = _format_arguments(item.args)
                    ret = (
                        f" -> {_format_annotation(item.returns)}" if item.returns else ""
                    )
                    lines.append(f"    {prefix} {item.name}({sig_args}){ret}: ...")
                    m_doc = _first_docstring_line(item)
                    if m_doc:
                        lines.append(f'        """{m_doc}"""')
            lines.append("")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            sig_args = _format_arguments(node.args)
            ret = f" -> {_format_annotation(node.returns)}" if node.returns else ""
            lines.append(f"{prefix} {node.name}({sig_args}){ret}: ...")
            doc = _first_docstring_line(node)
            if doc:
                lines.append(f'    """{doc}"""')
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Prompt caching helpers (Anthropic cache_control)
# ---------------------------------------------------------------------------


def build_prompt_cache_blocks(
    spec_path: str,
    user_prompt: str,
) -> list[dict[str, Any]]:
    """
    Build Anthropic message content with prompt caching enabled.

    The project spec (static, large) is marked ``cache_control: ephemeral``
    so the API caches it for ~5 minutes.  Only *user_prompt* (dynamic) is
    billed at full rate on subsequent calls.

    Savings: ~90 % reduction in input tokens during long coding sessions.
    """
    spec_path_obj = Path(spec_path)
    if not spec_path_obj.exists():
        logger.warning("build_prompt_cache_blocks: spec not found at %s", spec_path)
        spec_content = f"[Spec file not found: {spec_path}]"
    else:
        spec_content = spec_path_obj.read_text(encoding="utf-8")

    return [
        {
            "type": "text",
            "text": spec_content,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": user_prompt,
        },
    ]


# ---------------------------------------------------------------------------
# 5. Token estimation utility
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Rough token count: chars ÷ 4 (Anthropic approximate)."""
    return max(1, len(text) // _APPROX_CHARS_PER_TOKEN)


def token_savings_report(
    original_char_count: int,
    optimized_char_count: int,
) -> dict[str, Any]:
    """Return a dict summarising token savings for logging / telemetry."""
    original_tokens = estimate_tokens("x" * original_char_count)
    optimized_tokens = estimate_tokens("x" * optimized_char_count)
    saved = original_tokens - optimized_tokens
    pct = round((saved / original_tokens * 100) if original_tokens else 0, 1)
    return {
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": saved,
        "savings_pct": pct,
    }


# ---------------------------------------------------------------------------
# Convenience class wrapping all strategies
# ---------------------------------------------------------------------------


class TokenOptimizer:
    """
    Facade that bundles all four token-saving strategies.

    Instantiate once and inject into MCPGateway and LLMManager.
    """

    def __init__(
        self,
        max_head: int = _DEFAULT_HEAD_LINES,
        max_tail: int = _DEFAULT_TAIL_LINES,
    ) -> None:
        self.max_head = max_head
        self.max_tail = max_tail

    def prune_terminal_output(self, raw: str) -> str:
        """Delegate to module-level function with configured limits."""
        return prune_terminal_output(raw, self.max_head, self.max_tail)

    def apply_diff_patch(self, path: str, old_text: str, new_text: str) -> bool:
        """Delegate to module-level function."""
        return apply_diff_patch(path, old_text, new_text)

    def get_code_skeleton(self, path: str) -> str:
        """Delegate to module-level function."""
        return get_code_skeleton(path)

    def build_prompt_cache_blocks(
        self, spec_path: str, user_prompt: str
    ) -> list[dict[str, Any]]:
        """Delegate to module-level function."""
        return build_prompt_cache_blocks(spec_path, user_prompt)

    def estimate_tokens(self, text: str) -> int:
        """Delegate to module-level function."""
        return estimate_tokens(text)
