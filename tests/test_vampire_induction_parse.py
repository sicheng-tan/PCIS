"""Tests for Vampire --show_induction parsing and structured schemas."""

from __future__ import annotations

from vampire_runner import (
    parse_induction_trace_rich,
    structure_induction_formula,
)


SAMPLE_TRACE = """
[Induction] process zero != s(X0) in 7. zero != s(X0) [term algebras distinctness]
[Induction] process mul(sK0,sK1) != mul(sK1,sK0) in 19. mul(sK0,sK1) != mul(sK1,sK0) [cnf transformation 14]
[Induction] formula 20. ! [X0 : 'nat()'] : (mul(sK1,sK0) = mul(sK0,zero) & (mul(sK1,sK0) = mul(sK0,X0) => mul(sK1,sK0) = mul(sK0,s(X0)))) => ! [X1 : 'nat()'] : mul(sK1,sK0) = mul(sK0,X1) [structural induction hypothesis (one)]
[Induction] generate 24. mul(sK1,sK0) != mul(sK0,s(sK3)) | mul(sK1,sK0) != mul(sK0,zero) [generalized induction hyperresolution 19,23]
[Induction] formula 32. ! [X0 : 'nat()'] : (mul(sK0,zero) = mul(zero,sK0) & (mul(sK0,X0) = mul(X0,sK0) => mul(sK0,s(X0)) = mul(s(X0),sK0))) => ! [X1 : 'nat()'] : mul(sK0,X1) = mul(X1,sK0) [structural induction hypothesis (one)]
[Induction] generate 36. mul(sK0,s(sK5)) != mul(s(sK5),sK0) | mul(sK0,zero) != mul(zero,sK0) [induction hyperresolution 19,35]
"""


MULTILINE_TRACE = """
[Induction] formula 44.
! [X0 : 'nat()'] :
(mul(sK0,zero) = mul(zero,sK0) & (mul(sK0,X0) = mul(X0,sK0) => mul(sK0,s(X0)) = mul(s(X0),sK0))) => ! [X1 : 'nat()'] : mul(sK0,X1) = mul(X1,sK0)
[structural induction hypothesis (one)]
"""


def test_parse_does_not_truncate_formula_at_binder() -> None:
    trace = parse_induction_trace_rich(SAMPLE_TRACE)
    assert trace.formulas
    assert all(f.strip() not in ("!", "!!") for f in trace.formulas)
    assert any("mul(sK0,X1) = mul(X1,sK0)" in f for f in trace.formulas)
    assert any("mul(sK0,sK1) != mul(sK1,sK0)" in f for f in trace.focus)


def test_structure_extracts_var_sort_base_step() -> None:
    formula = (
        "! [X0 : 'nat()'] : (mul(sK0,zero) = mul(zero,sK0) & "
        "(mul(sK0,X0) = mul(X0,sK0) => mul(sK0,s(X0)) = mul(s(X0),sK0))) => "
        "! [X1 : 'nat()'] : mul(sK0,X1) = mul(X1,sK0) "
        "[structural induction hypothesis (one)]"
    )
    sch = structure_induction_formula(formula)
    assert sch["kind"] == "structural"
    assert sch["mode"] == "one"
    assert sch["induct_var"] == "X0"
    assert sch["induct_sort"] == "nat"
    assert "mul(sK0,zero)" in sch["base"]
    assert "=>" in sch["step"]
    assert "mul(sK0,X1)" in sch["conclusion"]
    assert "[structural" not in sch["raw"]


def test_multiline_formula_and_obligations() -> None:
    trace = parse_induction_trace_rich(SAMPLE_TRACE + MULTILINE_TRACE)
    assert trace.schemas
    assert any(s.get("induct_var") == "X0" for s in trace.schemas)
    assert any(s.get("induct_sort") == "nat" for s in trace.schemas)
    assert trace.obligations
    assert any("mul(sK0,s(sK5))" in o or "mul(sK0,zero)" in o for o in trace.obligations)

