"""Ablation switches for features added on top of the original PaperMate loop.

Kept for the paper portfolio: ``PROMPT_ADVICE``, ``PROBLEM_PROFILER``,
``INDUCTION_SCHEME``, ancestor / obligation-tree related knobs (PCR), and
strategy-mode prompt packs. Experimental routing / repair-hint / formula-
evidence / progress-sidecar / pattern-portfolio / proof-shape / prompt-retarget
switches have been removed.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence

_OFF_VALUES = frozenset({"0", "off", "false", "no"})

OURS_PROMPT_STRATEGIES = (
    "prove_prompt_equational_reasoning",
    "prove_prompt_term_rewrite",
)
NAIVE_PROMPT_STRATEGIES = ("prompt_naive",)
# v2: one generic template (lemma_general). Budget stays 2N.
V2_PROMPT_STRATEGIES = ("lemma_general",)
V2_LEMMA_GENERAL = "lemma_general"


def _flag_enabled(name: str, default: str = "on") -> bool:
    return os.getenv(name, default).strip().lower() not in _OFF_VALUES


def problem_profiler_enabled() -> bool:
    """Inject deterministic SMT structure facts into lemma-generation prompts.

    Parse / gate / render only. Default **off**. Does not call an LLM.
    Enable with ``PROBLEM_PROFILER=on``.
    """
    return _flag_enabled("PROBLEM_PROFILER", default="off")


def problem_profiler_min_attempt() -> int:
    """Earliest 1-based attempt index that may receive the profiler block.

    Default **1** (old behaviour). Set ``PROBLEM_PROFILER_MIN_ATTEMPT=2`` to
    skip the first generation attempt.
    """
    raw = (os.getenv("PROBLEM_PROFILER_MIN_ATTEMPT") or "1").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def problem_profiler_trigger() -> str:
    """When to inject relative to usefulness history.

    ``always`` (default): inject whenever attempt ≥ MIN_ATTEMPT.
    ``after_useless``: also require the last finished ``exp_attempts`` entry to
    have ``kind == "useless"`` (strict previous attempt).
    """
    raw = (os.getenv("PROBLEM_PROFILER_TRIGGER") or "always").strip().lower()
    if raw in ("after_useless", "useless", "last_useless"):
        return "after_useless"
    return "always"


def should_inject_problem_profiler(failed_data: Optional[dict] = None) -> bool:
    """Whether this lemma-generation call should append the profiler block."""
    if not problem_profiler_enabled():
        return False
    data = failed_data if isinstance(failed_data, dict) else {}
    attempts = data.get("exp_attempts") or []
    if not isinstance(attempts, list):
        attempts = []
    attempts_done = len(attempts)
    current_attempt = attempts_done + 1
    if current_attempt < problem_profiler_min_attempt():
        return False
    if problem_profiler_trigger() == "always":
        return True
    if attempts_done == 0:
        return False
    last = attempts[-1] if isinstance(attempts[-1], dict) else {}
    return str(last.get("kind") or "") == "useless"


def induction_scheme_enabled() -> bool:
    """Generate / short-prove structural (later measure) induction obligations.

    Default **off**. Enable with ``INDUCTION_SCHEME=on``. Does not put scheme
    formulas into usefulness C. Child nodes never call an LLM (v1).
    """
    return _flag_enabled("INDUCTION_SCHEME", default="off")


def induction_scheme_mode() -> str:
    """``structural`` | ``measure`` | ``both``. Unknown → structural.

    ``both``: short-prove all viable axes and merge nest/harvest (not
    winner-take-all by gate).
    """
    raw = (os.getenv("INDUCTION_SCHEME_MODE") or "structural").strip().lower()
    if raw in ("measure", "wellfounded", "wf"):
        return "measure"
    if raw in ("both", "all", "structural+measure"):
        return "both"
    return "structural"


def induction_scheme_trigger() -> str:
    """``always`` | ``after_useless`` (default)."""
    raw = (os.getenv("INDUCTION_SCHEME_TRIGGER") or "after_useless").strip().lower()
    if raw in ("always", "on"):
        return "always"
    return "after_useless"


def induction_scheme_goal_gate_enabled() -> bool:
    """Optional ``axioms ∧ library ∧ base/step ⊢ G`` check before structural prove.

    Default **on**. Hard fail (sat) drops that axis; timeout still allows
    obligation short-prove / NEST. Bridge-primary measure soft-skips the gate.
    ``INDUCTION_SCHEME_GOAL_GATE=off`` disables the check.
    """
    return _flag_enabled("INDUCTION_SCHEME_GOAL_GATE", default="on")


def induction_scheme_prompt_enabled() -> bool:
    """Inject the INDUCTION SCHEME ledger block into lemma prompts.

    Default **on** whenever scheme may run. Set ``INDUCTION_SCHEME_PROMPT=off``
    to keep generate/prove/NEST/harvest but omit the ledger from the LLM prompt
    (profiler PROBLEM STRUCTURE is unaffected).
    """
    return _flag_enabled("INDUCTION_SCHEME_PROMPT", default="on")


def induction_scheme_nest_policy() -> str:
    """Scheme→child nest policy: ``cross_sort`` | ``on`` | ``off``.

    Default **``cross_sort``**: nest only when a peek of ``select_induct_var`` on
    the child obligation would pick a **different** ADT/sort than the current
    scheme round (keeps Queue→Lst amortize paths; cuts Bin/Nat same-sort fanout).

    ``on``: previous behavior (any unproved structural base/step may nest).
    ``off``: never nest (frontier only).
    """
    raw = (os.getenv("INDUCTION_SCHEME_NEST") or "cross_sort").strip().lower()
    if raw in _OFF_VALUES:
        return "off"
    if raw in ("on", "all", "any", "same_ok", "same-ok"):
        return "on"
    if raw in ("cross_sort", "cross-sort", "cross"):
        return "cross_sort"
    return "cross_sort"


def should_run_induction_scheme(
    failed_data: Optional[dict] = None,
    *,
    scheme_only: bool = False,
) -> bool:
    """Whether this node/attempt should start a scheme generate+prove round.

    ``scheme_only`` nodes (NEST children) always run when the flag is on.
    Otherwise follows ``INDUCTION_SCHEME_TRIGGER`` against ``exp_attempts``.
    """
    if not induction_scheme_enabled():
        return False
    if scheme_only:
        return True
    data = failed_data if isinstance(failed_data, dict) else {}
    attempts = data.get("exp_attempts") or []
    if not isinstance(attempts, list):
        attempts = []
    if induction_scheme_trigger() == "always":
        return True
    if not attempts:
        return False
    last = attempts[-1] if isinstance(attempts[-1], dict) else {}
    return str(last.get("kind") or "") == "useless"


def prompt_advice_enabled() -> bool:
    """Emit LAST ATTEMPT advice labels (TRIGGER/BRIDGE/GENERALIZE/...).

    Independent of ``--strategy-mode``. Off keeps HD / library / INVALID
    without those labels.
    """
    return _flag_enabled("PROMPT_ADVICE")


def unproved_not_invalid_enabled() -> bool:
    """Situation A: useful-but-unproved stays off invalid_lemmas (default on).

    When on, blocking subgoals are recorded in ``unproved_lemmas``
    (USEFUL BUT UNPROVED) and copied to ``revival_lemmas`` for the diagnoser.
    When off, they are written to ``invalid_lemmas`` instead.
    """
    return _flag_enabled("UNPROVED_NOT_INVALID")


def ancestor_cycle_filter_enabled() -> bool:
    """Drop candidates α/eq-equivalent to a strict ancestor (path cycle)."""
    return _flag_enabled("ANCESTOR_CYCLE_FILTER")


def ancestor_prompt_enabled() -> bool:
    """Inject PROOF PATH GOALS (CURRENT + strict ancestors) into the user prompt."""
    return _flag_enabled("ANCESTOR_PROMPT")


# Fail-fast / child-budget switches live in lemma_gates.py (same default-on
# pattern). paper.env must set them off / CHILD_LLM_ATTEMPTS=0 / LLM_PARSE_RETRIES=0 / LLM_SCREEN_RETRIES=0.


def normalize_strategy_mode(strategy_mode: str) -> str:
    mode = (strategy_mode or "default").strip().lower().replace("-", "_")
    if mode in ("naive",):
        return "naive"
    if mode in ("zero_shot", "zeroshot"):
        return "zero_shot"
    if mode in ("v2_simple", "v2_compact", "general_ind_simple"):
        return "v2_simple"
    if mode in ("v2", "general_ind", "general_induction"):
        return "v2"
    if mode in ("default_simple", "ours_simple", "simple"):
        return "default_simple"
    if mode in ("default", "ours", ""):
        return "default"
    return "default"


def is_v2_strategy_mode(strategy_mode: str) -> bool:
    """True for ``v2`` and ``v2_simple`` (lemma_general pack)."""
    return normalize_strategy_mode(strategy_mode) in ("v2", "v2_simple")


def resolve_prompt_pack(
    strategy_mode: str,
    max_attempts_per_prompt: int,
) -> Dict[str, Any]:
    """Prompt folder, templates, and attempt budget for ``--strategy-mode``.

    ``MAX_ATTEMPTS_PER_PROMPT`` is N (default 3). Paper / ours uses N attempts
    on each of two templates (2N total). Naive uses the single ``prompt_naive``
    template 2N times so the LLM-call budget matches. ``zero_shot`` currently
    uses the same ours pack as ``default`` (no separate prompt folder).

    ``default_simple`` uses the same two template *names* as ``default``, but
    loads shortened system prompts from ``prompts_ours_compact``.

    ``v2`` uses ``prompts_v2`` with only ``lemma_general`` (budget 2N).
    ``v2_simple`` uses the same template name and budget from
    ``prompts_v2_compact``.
    """
    n = max(1, int(max_attempts_per_prompt) or 1)
    mode = normalize_strategy_mode(strategy_mode)
    if mode == "naive":
        strategies = list(NAIVE_PROMPT_STRATEGIES)
        return {
            "mode": mode,
            "folder_path": "./prompts_naive",
            "strategies": strategies,
            "max_attempts_per_prompt": n,
            "total_attempts": n * 2,
            "no_retarget_prompt": None,
        }
    if mode == "v2":
        strategies = list(V2_PROMPT_STRATEGIES)
        return {
            "mode": mode,
            "folder_path": "./prompts_v2",
            "strategies": strategies,
            "max_attempts_per_prompt": n,
            "total_attempts": n * 2,
            "no_retarget_prompt": V2_LEMMA_GENERAL,
        }
    if mode == "v2_simple":
        strategies = list(V2_PROMPT_STRATEGIES)
        return {
            "mode": mode,
            "folder_path": "./prompts_v2_compact",
            "strategies": strategies,
            "max_attempts_per_prompt": n,
            "total_attempts": n * 2,
            "no_retarget_prompt": V2_LEMMA_GENERAL,
        }
    if mode == "default_simple":
        strategies = list(OURS_PROMPT_STRATEGIES)
        return {
            "mode": mode,
            "folder_path": "./prompts_ours_compact",
            "strategies": strategies,
            "max_attempts_per_prompt": n,
            "total_attempts": n * len(strategies),
            "no_retarget_prompt": None,
        }
    strategies = list(OURS_PROMPT_STRATEGIES)
    return {
        "mode": mode,
        "folder_path": "./prompts_ours",
        "strategies": strategies,
        "max_attempts_per_prompt": n,
        "total_attempts": n * len(strategies),
        "no_retarget_prompt": None,
    }


def paper_schedule_prompt(
    strategies: Sequence[str],
    attempt: int,
    max_attempts_per_prompt: int,
) -> str:
    """Paper order: first template for N attempts, then the next, and so on."""
    pool = [s for s in strategies if s]
    if not pool:
        return ""
    per = max(1, int(max_attempts_per_prompt) or 1)
    idx = min(max(0, int(attempt)) // per, len(pool) - 1)
    return pool[idx]
