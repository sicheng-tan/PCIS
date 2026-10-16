#!/usr/bin/env python3
"""Apply mechanical strip to Mate_new_vampire.py mirroring cleaned Mate_new.py patterns."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

KILL = {
    "add_progress_lemma",
    "_compact_repair_hints",
    "add_repair_hints",
    "load_routing_state",
    "save_routing_state",
    "current_solver_profile",
    "seed_baseline_repair_hints",
    "select_attempt_action",
    "analyze_lemma_progress",
    "_progress_singleton_lemmas",
    "_record_failed_prove_diagnostics",
    "_record_failed_usefulness_mix",
    "record_solver_attempt",
    "_diag_profile",
    "record_child_profile_success",
    "record_usefulness_feedback",
    "record_attempt_solver_feedback",
    "attach_initial_prove_feedback",
}


def remove_funcs(src: str, names: set[str]) -> str:
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    cuts = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = node.lineno
            end = node.end_lineno or node.lineno
            if node.decorator_list:
                start = min(d.lineno for d in node.decorator_list)
            cuts.append((start, end))
    cuts.sort()
    out, i, ci = [], 1, 0
    while i <= len(lines):
        if ci < len(cuts) and i == cuts[ci][0]:
            i = cuts[ci][1] + 1
            while i <= len(lines) and lines[i - 1].strip() == "":
                i += 1
            ci += 1
            continue
        out.append(lines[i - 1])
        i += 1
    return "".join(out)


def main() -> None:
    path = ROOT / "Mate_new_vampire.py"
    text = path.read_text(encoding="utf-8")

    # Schema
    for s in (
        '"progress_lemmas": [],\n',
        '"progress_routing_signals": [],\n',
        '"repair_hints": [],\n',
        '"routing": {},\n',
        '"llm_hints": {},\n',
        'data.setdefault("progress_lemmas", [])\n',
        'data.setdefault("progress_routing_signals", [])\n',
        'data.setdefault("repair_hints", [])\n',
        'data.setdefault("routing", {})\n',
        'data.setdefault("llm_hints", {})\n',
    ):
        text = text.replace(s, "")

    # Drop deleted import blocks
    text = re.sub(r"from solver_routing import \([^)]*\)\n", "", text, flags=re.S)
    text = re.sub(r"from solver_routing import .*\n", "", text)
    text = re.sub(r"from profile_selector import \([^)]*\)\n", "", text, flags=re.S)
    text = re.sub(r"from profile_selector import .*\n", "", text)
    text = re.sub(r"from feedback_llm_hints import \([^)]*\)\n", "", text, flags=re.S)
    text = re.sub(r"from feedback_llm_hints import .*\n", "", text)

    text = remove_funcs(text, KILL)

    text = text.replace("run_vampire_routed(", "run_vampire_default(")
    text = re.sub(r",?\s*state\s*=\s*load_routing_state\([^)]*\)", "", text)
    text = re.sub(r",?\s*state\s*=\s*routing_state\b", "", text)
    text = re.sub(r",?\s*state\s*=\s*state\b", "", text)
    text = re.sub(r",?\s*state\s*=\s*GoalSearchState\([^)]*\)", "", text)

    for a, b in [
        ("routing_enabled()", "False"),
        ("probes_enabled()", "False"),
        ("llm_selector_enabled()", "False"),
        ("progress_feedback_enabled()", "False"),
        ("repair_hints_enabled()", "False"),
        ("vampire_collect_feedback_artifacts()", "False"),
        ("proof_shape_hint_enabled()", "False"),
        ("prompt_retarget_enabled()", "False"),
        ("prompt_retarget_active(", "False and ("),
    ]:
        text = text.replace(a, b)

    # Mark leftovers then drop lines
    for name in (
        "maybe_refresh_llm_hints",
        "derive_repair_hints",
        "add_repair_hints",
        "add_progress_lemma",
        "analyze_lemma_progress",
        "load_routing_state",
        "save_routing_state",
        "seed_baseline_repair_hints",
        "select_attempt_action",
        "retarget_generation_prompt",
        "format_routing_for_prompt",
        "select_generation_prompt",
        "choose_joint_action",
        "run_vampire_probe",
        "compute_progress_score",
        "GoalSearchState",
        "compact_repair_snapshot",
        "attach_source_lemmas",
        "should_append_proof_shape_hint",
        "PROOF_SHAPE_HINT_BLOCK",
        "record_solver_attempt",
        "build_search_state",
        "recommend_profiles",
        "set_routing_candidates",
        "rank_profiles_for_attempt",
        "fallback_profiles_for",
        "probe_profile_count",
        "probe_timeout_s",
        "profile_utility_from_stats",
        "apply_progress_routing",
        "record_pair_attempt",
        "record_profile_history",
    ):
        text = re.sub(rf"\b{name}\b", f"_REMOVED_{name}", text)

    lines = []
    for ln in text.splitlines(keepends=True):
        if "_REMOVED_" in ln:
            continue
        lines.append(ln)
    text = "".join(lines)

    # Force paper schedule: neutralize retarget blocks left as if False
    text = re.sub(r"retarget\s*=\s*False and \([^)]*\)", "retarget = False", text)
    text = re.sub(r"\nif False:\n(?:[ \t]+.+\n)+", "\n", text)

    # Ensure collect_difficulty import if missing; vampire may not need it
    if "collect_difficulty_for_feedback" not in text and "from exp_flags import" in text:
        text = text.replace(
            "from exp_flags import (",
            "from exp_flags import (\n    collect_difficulty_for_feedback,",
            1,
        )

    path.write_text(text, encoding="utf-8")
    try:
        ast.parse(text)
        print("Mate_new_vampire.py AST OK", file=sys.stderr)
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}", file=sys.stderr)
        # still write; fix manually
        sys.exit(1)
    print("done")


if __name__ == "__main__":
    main()
