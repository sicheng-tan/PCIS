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
    collect_difficulty_for_feedback,
    normalize_strategy_mode,
    paper_schedule_prompt,
    problem_profiler_enabled,
    prompt_advice_enabled,
    resolve_prompt_pack,
    unproved_not_invalid_enabled,
)
from lemma_gates import (
    defined_symbols_enabled,
    lemma_filter_drop_enabled,
    llm_lemma_diagnosis_enabled,
    llm_lemma_diagnosis_final_only,
    llm_invalid_ce_verify_enabled,
    llm_invalid_only_stop_enabled,
    subgoal_sat_abort_enabled,
)

_FLAG_NAMES = (
    "PROBLEM_PROFILER",
    "PROMPT_ADVICE",
    "UNPROVED_NOT_INVALID",
    "SUBGOAL_SAT_ABORT",
    "LEMMA_DEFINED_SYMBOLS",
    "LEMMA_FILTER_DROP",
    "LLM_LEMMA_DIAGNOSIS",
    "LLM_LEMMA_DIAGNOSIS_FINAL_ONLY",
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
        assert prompt_advice_enabled() is True
        assert unproved_not_invalid_enabled() is True
        assert subgoal_sat_abort_enabled() is True
        assert defined_symbols_enabled() is True
        assert lemma_filter_drop_enabled() is True
        assert llm_lemma_diagnosis_enabled() is True
        assert llm_lemma_diagnosis_final_only() is False
        assert llm_invalid_ce_verify_enabled() is False
        assert llm_invalid_only_stop_enabled() is True
        assert collect_difficulty_for_feedback() is True
    finally:
        _restore_flags(saved)
    for val in ("off", "0", "false", "no"):
        with patch.dict(os.environ, {"PROBLEM_PROFILER": val}):
            assert problem_profiler_enabled() is False
        with patch.dict(os.environ, {"PROMPT_ADVICE": val}):
            assert prompt_advice_enabled() is False
            assert collect_difficulty_for_feedback() is False
        with patch.dict(os.environ, {"UNPROVED_NOT_INVALID": val}):
            assert unproved_not_invalid_enabled() is False


def test_resolve_prompt_pack() -> None:
    ours = resolve_prompt_pack("default", 3)
    assert ours["folder_path"] == "./prompts_ours"
    assert ours["total_attempts"] == 6
    naive = resolve_prompt_pack("naive", 3)
    assert naive["folder_path"] == "./prompts_naive"
    assert naive["total_attempts"] == 6
    v2 = resolve_prompt_pack("v2", 3)
    assert v2["mode"] == "v2"
    assert v2["no_retarget_prompt"] == "lemma_general"
    assert normalize_strategy_mode("general_ind") == "v2"


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
