#!/usr/bin/env python3
"""Tests for PCR/GSE ablation flags in exp_flags and lemma_gates."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OPENAI_API_KEY", "unit-test-placeholder")
os.environ.setdefault("MODEL_TYPE", "gpt-4o")

from exp_flags import (
    ancestor_cycle_filter_enabled,
    ancestor_prompt_enabled,
    induction_scheme_enabled,
    induction_scheme_mode,
    induction_scheme_nest_policy,
    normalize_strategy_mode,
    paper_schedule_prompt,
    problem_profiler_enabled,
    resolve_prompt_pack,
    should_inject_problem_profiler,
    should_run_induction_scheme,
    unproved_not_invalid_enabled,
)
from proof_context_reuse.lemma_gates import (
    defined_symbols_enabled,
    lemma_filter_drop_enabled,
    llm_invalid_ce_verify_enabled,
    llm_invalid_only_stop_enabled,
    should_accept_in_loop_invalid_goal,
    subgoal_sat_abort_enabled,
)
from proof_context_reuse.obligation_tree import (
    invalid_lemmas_mode,
    invalid_lemmas_paper_mode,
    lemma_library_enabled,
    obligation_tree_enabled,
)

_FLAG_NAMES = (
    "PROBLEM_PROFILER",
    "UNPROVED_NOT_INVALID",
    "SUBGOAL_SAT_ABORT",
    "LEMMA_DEFINED_SYMBOLS",
    "LEMMA_FILTER_DROP",
    "LLM_INVALID_CE_VERIFY",
    "LLM_INVALID_CE_RETRIES",
    "LLM_INVALID_ONLY_STOP",
)

_GOAL_SMT = """(set-logic ALL)
(declare-fun P (Int) Bool)
; proof goal
(assert (not (forall ((x Int)) (P x))))
; proof goal end
(check-sat)
"""

_FEEDBACK_PAYLOAD = {
    "invalid_lemmas": [],
    "useless_lemma_groups": [{"lemmas": ["(L1)"], "status": "timeout"}],
    "unproved_lemmas": [{"lemma": "(L2)", "status": "useful_but_unproved"}],
    "last_screen": [],
    "exp_attempts": [],
}


def _clear_flags():
    return {name: os.environ.pop(name) for name in _FLAG_NAMES if name in os.environ}


def _restore_flags(saved):
    for name in _FLAG_NAMES:
        os.environ.pop(name, None)
    os.environ.update(saved)


def test_flags_default_on() -> None:
    saved = _clear_flags()
    try:
        assert problem_profiler_enabled() is False
        assert unproved_not_invalid_enabled() is True
        assert subgoal_sat_abort_enabled() is True
        assert defined_symbols_enabled() is True
        assert lemma_filter_drop_enabled() is True
        assert llm_invalid_ce_verify_enabled() is False
        assert llm_invalid_only_stop_enabled() is True
    finally:
        _restore_flags(saved)
    for val in ("off", "0", "false", "no"):
        with patch.dict(os.environ, {"PROBLEM_PROFILER": val}):
            assert problem_profiler_enabled() is False
        with patch.dict(os.environ, {"UNPROVED_NOT_INVALID": val}):
            assert unproved_not_invalid_enabled() is False


def test_resolve_prompt_pack() -> None:
    ours = resolve_prompt_pack("default", 3)
    assert ours["folder_path"] == "./prompts_ours"
    assert ours["total_attempts"] == 6
    naive = resolve_prompt_pack("naive", 3)
    assert naive["folder_path"] == "./prompts_naive"
    assert naive["total_attempts"] == 6
    assert normalize_strategy_mode("v2") == "default"
    assert normalize_strategy_mode("general_ind") == "default"
    compact = resolve_prompt_pack("default_simple", 3)
    assert compact["folder_path"] == "./prompts_ours_compact"


def test_paper_schedule_prompt() -> None:
    strats = ["prove_prompt_equational_reasoning", "prove_prompt_term_rewrite"]
    assert paper_schedule_prompt(strats, 0, 3) == "prove_prompt_equational_reasoning"
    assert paper_schedule_prompt(strats, 3, 3) == "prove_prompt_term_rewrite"
    assert paper_schedule_prompt([], 0, 3) == ""


def test_naive_strategy_repeats_prompt_naive() -> None:
    import Mate_new as mate

    calls: list[str] = []

    def fake_quick_run(_base, _name, prompt_strategy, folder_path, *_args, **_kwargs):
        calls.append((prompt_strategy, folder_path))
        return False, [], []

    saved = _clear_flags()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "template.smt2").write_text(_GOAL_SMT, encoding="utf-8")
            with patch("Mate_new.perform_initial_verification", return_value=False), patch(
                "Mate_new.quick_run", side_effect=fake_quick_run
            ), patch.dict(mate.config, {"MAX_ATTEMPTS_PER_PROMPT": 3}):
                assert mate.prove_run(tmp, "template", strategy_mode="naive") is False
    finally:
        _restore_flags(saved)

    assert len(calls) == 6
    assert all(name == "prompt_naive" for name, _folder in calls)


def test_prompt_retarget_off_uses_paper_order() -> None:
    import Mate_new as mate

    calls: list[str] = []

    def fake_quick_run(_base, _name, prompt_strategy, *_args, **_kwargs):
        calls.append(prompt_strategy)
        return False, [], []

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "template.smt2").write_text(_GOAL_SMT, encoding="utf-8")
        with patch("Mate_new.perform_initial_verification", return_value=False), patch(
            "Mate_new.quick_run", side_effect=fake_quick_run
        ), patch.dict(mate.config, {"MAX_ATTEMPTS_PER_PROMPT": 3}):
            assert mate.prove_run(tmp, "template") is False

    assert calls == (
        ["prove_prompt_equational_reasoning"] * 3
        + ["prove_prompt_term_rewrite"] * 3
    )


def test_format_solver_feedback_pcr_sections() -> None:
    import Mate_new as mate

    with patch.dict(os.environ, {"UNPROVED_NOT_INVALID": "on"}):
        txt = mate.format_solver_feedback_for_prompt(_FEEDBACK_PAYLOAD)
    assert "LAST ATTEMPT" in txt
    assert "USEFUL BUT UNPROVED" in txt
    assert "SOLVER PROGRESS SIGNALS" not in txt
    assert "SOLVER ROUTING" not in txt
    assert "    advice:" not in txt

    with patch.dict(os.environ, {"UNPROVED_NOT_INVALID": "off"}):
        off_txt = mate.format_solver_feedback_for_prompt(_FEEDBACK_PAYLOAD)
    assert "USEFUL BUT UNPROVED" not in off_txt


def test_unproved_flag_writes_unproved() -> None:
    import Mate_new as mate
    from cvc5_runner import CvcResult

    child = CvcResult(status="timeout", stats={"INST_TOTAL": 2}, strategy="cvc5_inductive")
    with tempfile.TemporaryDirectory() as tmp:
        mate._store_cached_diag(tmp, "template_1", "baseline_diag", child)
        with patch.dict(os.environ, {"UNPROVED_NOT_INVALID": "on"}):
            mate._record_subgoal_failure_feedback(
                tmp, "template", "template_1", ["(assert true)"]
            )
        parent = mate.load_failed_lemmas(tmp, "template")
        assert parent["invalid_lemmas"] == []
        assert len(parent["unproved_lemmas"]) == 1


def test_vampire_paper_order() -> None:
    import Mate_new_vampire as mate_v

    calls: list[str] = []

    def fake_quick(_base, _name, prompt_strategy, *_args, **_kwargs):
        calls.append(prompt_strategy)
        return False, [], []

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "template.smt2").write_text(_GOAL_SMT, encoding="utf-8")
        with patch(
            "Mate_new_vampire.perform_initial_verification", return_value=False
        ), patch("Mate_new_vampire.quick_run", side_effect=fake_quick), patch.dict(
            mate_v.config, {"MAX_ATTEMPTS_PER_PROMPT": 3}
        ):
            assert mate_v.prove_run(tmp, "template") is False
    assert calls[:3] == ["prove_prompt_equational_reasoning"] * 3
    assert calls[3:] == ["prove_prompt_term_rewrite"] * 3


def test_main_ablation_matrix_flags() -> None:
    """PCR / GSE / PCIS switch matrix from the paper main table."""
    useless = {"exp_attempts": [{"kind": "useless"}]}

    pcr = {
        "LEMMA_LIBRARY": "on",
        "OBLIGATION_TREE": "on",
        "INVALID_LEMMAS": "on",
        "LEMMA_LIBRARY_LOCAL": "on",
        "ANCESTOR_CYCLE_FILTER": "on",
        "ANCESTOR_PROMPT": "on",
        "UNPROVED_NOT_INVALID": "on",
        "PROBLEM_PROFILER": "off",
        "INDUCTION_SCHEME": "off",
        "LLM_INVALID_ONLY_STOP": "on",
    }
    with patch.dict(os.environ, pcr, clear=False):
        assert lemma_library_enabled() and obligation_tree_enabled()
        assert invalid_lemmas_mode() == "on" and not invalid_lemmas_paper_mode()
        assert unproved_not_invalid_enabled()
        assert not problem_profiler_enabled() and not induction_scheme_enabled()
        assert llm_invalid_only_stop_enabled()
        assert should_accept_in_loop_invalid_goal(1)
        assert not should_accept_in_loop_invalid_goal(0)

    gse = {
        "LEMMA_LIBRARY": "off",
        "OBLIGATION_TREE": "off",
        "INVALID_LEMMAS": "paper",
        "LEMMA_LIBRARY_LOCAL": "off",
        "ANCESTOR_CYCLE_FILTER": "off",
        "ANCESTOR_PROMPT": "off",
        "UNPROVED_NOT_INVALID": "off",
        "PROBLEM_PROFILER": "on",
        "PROBLEM_PROFILER_MIN_ATTEMPT": "2",
        "PROBLEM_PROFILER_TRIGGER": "after_useless",
        "INDUCTION_SCHEME": "on",
        "INDUCTION_SCHEME_MODE": "both",
        "INDUCTION_SCHEME_TRIGGER": "after_useless",
        "INDUCTION_SCHEME_NEST": "cross_sort",
        "LLM_INVALID_ONLY_STOP": "on",
    }
    with patch.dict(os.environ, gse, clear=False):
        assert not lemma_library_enabled() and not obligation_tree_enabled()
        assert invalid_lemmas_paper_mode() and not unproved_not_invalid_enabled()
        assert not ancestor_cycle_filter_enabled() and not ancestor_prompt_enabled()
        assert problem_profiler_enabled() and induction_scheme_enabled()
        assert induction_scheme_mode() == "both"
        assert induction_scheme_nest_policy() == "cross_sort"
        assert should_inject_problem_profiler(useless)
        assert should_run_induction_scheme(useless)
        assert not should_inject_problem_profiler({"exp_attempts": []})

    pcis = {
        **pcr,
        "PROBLEM_PROFILER": "on",
        "PROBLEM_PROFILER_MIN_ATTEMPT": "2",
        "PROBLEM_PROFILER_TRIGGER": "after_useless",
        "INDUCTION_SCHEME": "on",
        "INDUCTION_SCHEME_MODE": "both",
        "INDUCTION_SCHEME_TRIGGER": "after_useless",
        "INDUCTION_SCHEME_NEST": "cross_sort",
    }
    with patch.dict(os.environ, pcis, clear=False):
        assert lemma_library_enabled() and obligation_tree_enabled()
        assert problem_profiler_enabled() and induction_scheme_enabled()
        assert should_inject_problem_profiler(useless)
        assert should_run_induction_scheme(useless)
