"""Tests for SMT-LIB formula helpers (normalize / assert wrap)."""

from __future__ import annotations

from smt_patterns import (
    equality_lhs,
    format_assert_line,
    has_directed_equality,
    infer_trigger_pattern,
    strip_bang_attrs,
)
from obligation_tree import inject_library_axioms


def _ok(cond: bool, msg: str = "") -> None:
    assert cond, msg


def test_infer_pattern_on_directed_eq() -> None:
    f = "(forall ((x Bin) (y Bin)) (= (plus (s x) y) (s (plus x y))))"
    _ok(has_directed_equality(f), "directed")
    _ok(equality_lhs(f) == "(plus (s x) y)", equality_lhs(f))
    _ok(infer_trigger_pattern(f) == "((plus (s x) y))", infer_trigger_pattern(f))
    line = format_assert_line(f, add_pattern=True)
    _ok(line.startswith("(assert (! "), line)
    _ok(":pattern ((plus (s x) y))" in line, line)
    bare = format_assert_line(f, add_pattern=False)
    _ok(bare == f"(assert {f})", bare)
    named = format_assert_line(f, named="C1")
    _ok(":named C1" in named and f in named, named)
    both = format_assert_line(f, add_pattern=True, named="C1")
    _ok(":named C1" in both and ":pattern ((plus (s x) y))" in both, both)


def test_pattern_skips_var_eq_and_implications() -> None:
    _ok(not has_directed_equality("(forall ((x Nat)) (= x x))"))
    f = "(forall ((x Nat)) (=> (P x) (= (f x) (g x))))"
    _ok(has_directed_equality(f), f)
    _ok(infer_trigger_pattern(f) == "((f x))", infer_trigger_pattern(f))


def test_strip_bang_attrs() -> None:
    raw = "(! (forall ((x Nat)) (= (f x) x)) :pattern ((f x)))"
    _ok(strip_bang_attrs(raw) == "(forall ((x Nat)) (= (f x) x))", strip_bang_attrs(raw))


def test_inject_library_with_patterns() -> None:
    smt = """(set-logic ALL)
; proof goal
(assert (not true))
; proof goal end
"""
    formula = "(forall ((x Nat)) (= (plus x zero) x))"
    out = inject_library_axioms(
        smt,
        [{"id": "lib_1", "formula": formula}],
        add_patterns=True,
    )
    _ok("(assert (! (forall ((x Nat)) (= (plus x zero) x)) :pattern ((plus x zero)))" in out, out)
    bare = inject_library_axioms(
        smt,
        [{"id": "lib_1", "formula": formula}],
        add_patterns=False,
    )
    _ok(f"(assert {formula})" in bare, bare)
    _ok(":pattern" not in bare, bare)


def main() -> None:
    test_infer_pattern_on_directed_eq()
    test_pattern_skips_var_eq_and_implications()
    test_strip_bang_attrs()
    test_inject_library_with_patterns()
    print("ok")


if __name__ == "__main__":
    main()
