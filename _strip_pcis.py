#!/usr/bin/env python3
"""Complete strip of deleted experimental modules from PCIS sources."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

KILL_FUNCS_MATE = {
    "add_progress_lemma",
    "_compact_repair_hints",
    "add_repair_hints",
    "load_routing_state",
    "save_routing_state",
    "current_solver_profile",
    "record_child_profile_success",
    "record_usefulness_feedback",
    "record_attempt_solver_feedback",
    "attach_initial_prove_feedback",
    "seed_baseline_repair_hints",
    "select_attempt_action",
    "analyze_lemma_progress",
    "_remember_cvc_patterns",
    "_resolve_cvc_add_patterns",
    "_progress_singleton_lemmas",
    "_record_failed_prove_diagnostics",
    "_record_failed_usefulness_mix",
    "record_solver_attempt",
    "_diag_profile",
}

KILL_FUNCS_RUNNER = {
    "compute_progress_score",
    "derive_repair_hints",
    "run_cvc_routed",
    "run_cvc_probe",
    "cvc_probeable_profiles",
    "run_vampire_routed",
    "run_vampire_probe",
    "parse_cvc_lemmas",
    "select_formula_evidence_samples",
}


def remove_funcs(src: str, names: set[str]) -> tuple[str, list[str]]:
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    cuts: list[tuple[int, int]] = []
    removed: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = node.lineno
            end = node.end_lineno or node.lineno
            if node.decorator_list:
                start = min(d.lineno for d in node.decorator_list)
            cuts.append((start, end))
            removed.append(node.name)
    if not cuts:
        return src, []
    cuts.sort()
    out: list[str] = []
    i = 1
    cut_i = 0
    while i <= len(lines):
        if cut_i < len(cuts) and i == cuts[cut_i][0]:
            i = cuts[cut_i][1] + 1
            while i <= len(lines) and lines[i - 1].strip() == "":
                i += 1
            cut_i += 1
            continue
        out.append(lines[i - 1])
        i += 1
    return "".join(out), removed


def strip_import_blocks(text: str) -> str:
    # Drop whole from-import blocks that only pull deleted modules.
    text = re.sub(
        r"from solver_routing import \([^)]*\)\n",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(r"from solver_routing import .*\n", "", text)
    text = re.sub(
        r"from profile_selector import \([^)]*\)\n",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(r"from profile_selector import .*\n", "", text)
    text = re.sub(
        r"from feedback_llm_hints import \([^)]*\)\n",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(r"from feedback_llm_hints import .*\n", "", text)
    return text


def neutralize_calls(text: str, *, vampire: bool) -> str:
    if vampire:
        text = text.replace("run_vampire_routed(", "run_vampire_default(")
    else:
        text = text.replace("run_cvc_routed(", "run_cvc(")

    # Remove state= kwargs commonly used with routed runners.
    text = re.sub(r",?\s*state\s*=\s*load_routing_state\([^)]*\)", "", text)
    text = re.sub(r",?\s*state\s*=\s*routing_state\b", "", text)
    text = re.sub(r",?\s*state\s*=\s*state\b", "", text)
    text = re.sub(r",?\s*state\s*=\s*GoalSearchState\([^)]*\)", "", text)

    replacements = {
        "routing_enabled()": "False",
        "probes_enabled()": "False",
        "llm_selector_enabled()": "False",
        "progress_feedback_enabled()": "False",
        "repair_hints_enabled()": "False",
        "collect_difficulty_for_feedback()": "collect_difficulty_for_feedback()",
        "vampire_collect_feedback_artifacts()": "False",
        "formula_evidence_enabled()": "False",
        "feedback_llm_hints_enabled()": "False",
        "feedback_llm_hints_hd_enabled()": "False",
        "proof_shape_hint_enabled()": "False",
        "cvc_patterns_enabled()": "False",
        "prompt_retarget_enabled()": "False",
    }
    # Keep collect_difficulty if still imported from exp_flags.
    for old, new in replacements.items():
        if old != new:
            text = text.replace(old, new)

    text = re.sub(
        r"retarget\s*=\s*prompt_retarget_active\([^)]*\)",
        "retarget = False",
        text,
    )
    text = re.sub(
        r"patterns_enabled\s*=\s*resolve_cvc_patterns_enabled\([^)]*\)",
        "patterns_enabled = False",
        text,
    )
    text = re.sub(
        r"enabled\s*=\s*resolve_cvc_patterns_enabled\([^)]*\)",
        "enabled = False",
        text,
    )

    # Mark remaining deleted symbols so we can drop lines.
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
        "run_cvc_probe",
        "run_vampire_probe",
        "cvc_probeable_profiles",
        "compute_progress_score",
        "GoalSearchState",
        "compact_repair_snapshot",
        "attach_source_lemmas",
        "should_append_proof_shape_hint",
        "PROOF_SHAPE_HINT_BLOCK",
        "should_add_cvc_patterns",
        "resolve_cvc_patterns_enabled",
        "apply_cvc_patterns_cli",
        "prompt_retarget_active",
        "_remember_cvc_patterns",
        "_resolve_cvc_add_patterns",
        "record_solver_attempt",
        "_record_failed_prove_diagnostics",
        "_record_failed_usefulness_mix",
        "_progress_singleton_lemmas",
        "format_routing_guidance",
        "preferred_prompt_for_hints",
        "apply_progress_routing",
        "rank_profiles_for_attempt",
        "recommend_profiles",
        "recommend_cvc5_profiles",
        "recommend_vampire_profiles",
    ):
        text = text.replace(f"{name}(", f"_REMOVED_{name}(")
        text = text.replace(f"{name}.", f"_REMOVED_{name}.")
        # bare name in types / imports
        text = re.sub(rf"\b{name}\b", f"_REMOVED_{name}", text)

    return text


def drop_removed_lines(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out = []
    skip_until_dedent = None
    for line in lines:
        if "_REMOVED_" in line:
            # Drop the line; if it opens an if/for/with, also skip body roughly
            # by tracking indent — conservative: only drop this line.
            continue
        out.append(line)
    return "".join(out)


def clean_mate_schema(text: str) -> str:
    text = text.replace('"progress_lemmas": [],\n', "")
    text = text.replace('"progress_routing_signals": [],\n', "")
    text = text.replace('"repair_hints": [],\n', "")
    text = text.replace('"routing": {},\n', "")
    text = text.replace('"llm_hints": {},\n', "")
    text = text.replace('data.setdefault("progress_lemmas", [])\n', "")
    text = text.replace('data.setdefault("progress_routing_signals", [])\n', "")
    text = text.replace('data.setdefault("repair_hints", [])\n', "")
    text = text.replace('data.setdefault("routing", {})\n', "")
    text = text.replace('data.setdefault("llm_hints", {})\n', "")
    return text


def clean_imports_mate(text: str) -> str:
    # Remove deleted names from exp_flags / lemma_gates / smt_patterns imports.
    kill_names = {
        "repair_hints_enabled",
        "progress_feedback_enabled",
        "formula_evidence_enabled",
        "feedback_llm_hints_enabled",
        "feedback_llm_hints_hd_enabled",
        "proof_shape_hint_enabled",
        "prompt_retarget_enabled",
        "prompt_retarget_active",
        "cvc_patterns_enabled",
        "resolve_cvc_patterns_enabled",
        "apply_cvc_patterns_cli",
        "vampire_collect_feedback_artifacts",
        "should_append_proof_shape_hint",
        "PROOF_SHAPE_HINT_BLOCK",
        "compact_repair_snapshot",
        "attach_source_lemmas",
        "should_add_cvc_patterns",
        "v2_should_add_cvc_patterns",
        "pattern_trigger_reasons",
        "derive_repair_hints",
        "compute_progress_score",
        "run_cvc_routed",
        "run_vampire_routed",
        "GoalSearchState",
        "routing_enabled",
        "probes_enabled",
        "llm_selector_enabled",
        "format_routing_for_prompt",
        "maybe_refresh_llm_hints",
    }

    def filter_import_list(block: str) -> str:
        lines = block.splitlines(keepends=True)
        kept = []
        for ln in lines:
            name = ln.strip().rstrip(",").strip()
            if name in kill_names:
                continue
            # also "name as alias"
            base = name.split(" as ")[0].strip()
            if base in kill_names:
                continue
            kept.append(ln)
        return "".join(kept)

    def repl_from(m: re.Match) -> str:
        head, body, tail = m.group(1), m.group(2), m.group(3)
        filtered = filter_import_list(body)
        if not any(
            ln.strip() and not ln.strip().startswith("#") and ln.strip() != ")"
            for ln in filtered.splitlines()
        ):
            return ""
        # ensure trailing comma hygiene
        return f"{head}{filtered}{tail}"

    text = re.sub(
        r"(from\s+\S+\s+import\s*\()(.*?)(\n\))",
        repl_from,
        text,
        flags=re.S,
    )
    return text


def fix_prove_run_loop(text: str) -> str:
    """Force paper schedule; drop routing select_attempt blocks when emptied."""
    # After drop_removed_lines, retarget=False already; ensure paper schedule used.
    text = re.sub(
        r"if retarget:\n(?:[ \t]+.+\n)+",
        "",
        text,
    )
    text = re.sub(
        r"if False:\n(?:[ \t]+.+\n)+",
        "",
        text,
    )
    return text


def strip_mate(path: Path, *, vampire: bool) -> None:
    text = path.read_text(encoding="utf-8")
    text = strip_import_blocks(text)
    text = clean_imports_mate(text)
    text = clean_mate_schema(text)
    text, removed = remove_funcs(text, KILL_FUNCS_MATE)
    print(f"{path.name}: removed defs {removed}")
    text = neutralize_calls(text, vampire=vampire)
    text = drop_removed_lines(text)
    text = fix_prove_run_loop(text)
    # Drop cvc_patterns params in signatures (optional cleanup — leave unused kwargs ok)
    text = re.sub(
        r",?\n\s*cvc_patterns: Optional\[bool\] = None",
        "",
        text,
    )
    text = re.sub(r",?\s*cvc_patterns=patterns_enabled", "", text)
    text = re.sub(r",?\s*cvc_patterns=cvc_patterns", "", text)
    text = re.sub(r",?\s*cvc_patterns=None", "", text)
    path.write_text(text, encoding="utf-8")
    try:
        ast.parse(text)
        print(f"{path.name}: AST OK")
    except SyntaxError as e:
        print(f"{path.name}: SYNTAX ERROR {e}")
        sys.exit(1)


def strip_runner(path: Path, kill: set[str]) -> None:
    text = path.read_text(encoding="utf-8")
    text = strip_import_blocks(text)
    text = text.replace("from exp_flags import formula_evidence_enabled\n", "")
    text = text.replace("from exp_flags import (\n", "from exp_flags import (\n")
    text, removed = remove_funcs(text, kill)
    print(f"{path.name}: removed defs {removed}")
    # Remove -o lemmas formula evidence blocks if gated
    text = re.sub(
        r"\n\s*if formula_evidence_enabled\(\):.*?(?=\n\S|\Z)",
        "\n",
        text,
        flags=re.S,
    )
    text = neutralize_calls(text, vampire="vampire" in path.name)
    text = drop_removed_lines(text)
    path.write_text(text, encoding="utf-8")
    try:
        ast.parse(text)
        print(f"{path.name}: AST OK")
    except SyntaxError as e:
        print(f"{path.name}: SYNTAX ERROR {e}")


def main() -> None:
    strip_mate(ROOT / "Mate_new.py", vampire=False)
    strip_mate(ROOT / "Mate_new_vampire.py", vampire=True)
    strip_runner(ROOT / "cvc5_runner.py", KILL_FUNCS_RUNNER)
    strip_runner(ROOT / "vampire_runner.py", KILL_FUNCS_RUNNER)
    print("strip phase done")


if __name__ == "__main__":
    main()
