"""SMT-LIB formula helpers used by PCR/GSE inject paths.

Includes s-expression readers, lemma normalization, and optional
``:pattern`` / ``:named`` wrapping for ``(assert ...)`` lines.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

_BANG_ATTR = re.compile(r"\(\s*!\s+")


def normalize_lemma_formula(formula: str) -> str:
    return re.sub(r"\s+", " ", (formula or "").strip())


def _skip_ws(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    return i


def read_sexpr(text: str, i: int = 0) -> Tuple[Optional[str], int]:
    """Read one SMT-LIB s-expression starting at ``i``; return (expr, next_i)."""
    i = _skip_ws(text, i)
    n = len(text)
    if i >= n:
        return None, i
    if text[i] != "(":
        j = i
        while j < n and not text[j].isspace() and text[j] not in "()":
            j += 1
        return text[i:j], j
    depth = 0
    j = i
    while j < n:
        ch = text[j]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[i : j + 1], j + 1
        j += 1
    return None, i


def sexpr_head_args(expr: str) -> Tuple[Optional[str], List[str]]:
    """Split ``(head arg...)`` into head token and argument s-exprs."""
    text = (expr or "").strip()
    if not text.startswith("("):
        return None, []
    inner = text[1:-1].strip() if text.endswith(")") else text[1:].strip()
    head, i = read_sexpr(inner, 0)
    if head is None:
        return None, []
    args: List[str] = []
    n = len(inner)
    while True:
        i = _skip_ws(inner, i)
        if i >= n:
            break
        arg, i = read_sexpr(inner, i)
        if arg is None:
            break
        args.append(arg)
    return head, args


def strip_bang_attrs(formula: str) -> str:
    """Unwrap ``(! φ :attr ...)`` layers, keeping φ."""
    text = normalize_lemma_formula(formula)
    while True:
        m = _BANG_ATTR.match(text)
        if not m:
            return text
        body, i = read_sexpr(text, m.end())
        if body is None:
            return text
        # Skip trailing attributes until the closing ')' of the bang form.
        # text is "(! BODY :attr ...)" — BODY already consumed; drop rest.
        text = normalize_lemma_formula(body)


def forall_matrix(formula: str) -> str:
    """Return the body of the outermost ``forall``, else the formula itself."""
    text = strip_bang_attrs(formula)
    head, args = sexpr_head_args(text)
    if head != "forall" or len(args) < 2:
        return text
    return strip_bang_attrs(args[-1])


def peel_implication(body: str) -> str:
    """Follow ``=>`` / ``implies`` to the conclusion."""
    text = strip_bang_attrs(body)
    while True:
        head, args = sexpr_head_args(text)
        if head in ("=>", "implies") and len(args) >= 2:
            text = strip_bang_attrs(args[-1])
            continue
        return text


def equality_lhs(formula: str) -> Optional[str]:
    """LHS of a top-level / conclusion ``(= L R)``, or None."""
    body = peel_implication(forall_matrix(formula))
    head, args = sexpr_head_args(body)
    if head != "=" or len(args) < 2:
        return None
    return args[0].strip() or None


def is_app_term(term: str) -> bool:
    """True for compound applications ``(f ...)`` (good E-matching triggers)."""
    text = (term or "").strip()
    if not text.startswith("("):
        return False
    head, _args = sexpr_head_args(text)
    if head is None:
        return False
    # Indexed identifiers like (_ BitVec 8) are not useful triggers alone.
    if head == "_":
        return False
    return True


def has_directed_equality(formula: str) -> bool:
    lhs = equality_lhs(formula)
    return bool(lhs and is_app_term(lhs))


def formulas_have_directed_equality(formulas: Sequence[str]) -> bool:
    return any(has_directed_equality(f) for f in formulas if f)


def infer_trigger_pattern(formula: str) -> Optional[str]:
    """Return a ``:pattern`` value like ``((plus (s x) y))``, or None."""
    lhs = equality_lhs(formula)
    if not lhs or not is_app_term(lhs):
        return None
    return f"({lhs})"


def candidate_lemma_id(index: int) -> str:
    """Stable SMT ``:named`` id for mix-round generated lemma ``index`` (1-based)."""
    return f"C{int(index)}"


def format_assert_line(
    formula: str,
    *,
    add_pattern: bool = False,
    named: Optional[str] = None,
) -> str:
    """``(assert φ)`` or ``(assert (! φ :named C1 :pattern …))``."""
    text = normalize_lemma_formula(formula)
    if text.startswith("(assert"):
        inner, _ = read_sexpr(text, 0)
        if inner and inner.startswith("(assert"):
            head, args = sexpr_head_args(inner)
            if head == "assert" and args:
                text = normalize_lemma_formula(args[0])
    text = strip_bang_attrs(text)
    attrs: List[str] = []
    label = str(named or "").strip()
    if label:
        attrs.append(f":named {label}")
    if add_pattern:
        pat = infer_trigger_pattern(text)
        if pat:
            attrs.append(f":pattern {pat}")
    if attrs:
        return f"(assert (! {text} {' '.join(attrs)}))"
    return f"(assert {text})"
