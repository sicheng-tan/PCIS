#!/usr/bin/env python3
"""
Main program entry.
Invokes the solver API from Mate_new.py.
"""

import argparse
import logging
import sys

import Mate_new as mate_solver

prove_run = mate_solver.prove_run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProofMate single-task entry")
    parser.add_argument("base_path")
    parser.add_argument("base_name")
    parser.add_argument(
        "--strategy-mode",
        choices=["default", "default_simple", "zero_shot", "naive"],
        default="default",
        help="default: prompts_ours; default_simple: prompts_ours_compact (same two modes); "
        "zero_shot: same as default; naive: prompt_naive × 2N",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Solver initial verification only; do not call the LLM",
    )
    args = parser.parse_args()

    final_status = prove_run(
        args.base_path,
        args.base_name,
        strategy_mode=args.strategy_mode,
        baseline_only=args.baseline,
    )

    logging.info("Final verification result: %s", "Success" if final_status else "Fail")
    logging.info("unsat" if final_status else "")
    sys.exit(0 if final_status else 1)
