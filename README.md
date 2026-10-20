# PCIS

**PCIS** = LLM4Ind-style lemma search + **PCR** (proof-context retrieval / memory) + **GSE** (problem profiler + induction scheme).

This repository is the paper pipeline for evaluating PCIS on inductive SMT-LIB tasks (CVC5/CVC4 portfolio or Vampire). Non-paper experiment modules (solver routing, LLM feedback hints, `PROMPT_ADVICE`, lemma diagnosis, etc.) have been removed.

Base search idea follows:

> *Can LLM Aid in Solving Constraints with Inductive Definitions?*  
> Full version: https://doi.org/10.48550/arXiv.2603.03668

---

## Remaining documentation

| Path | Role |
|------|------|
| `README.md` | This file — setup, modules, how to run |
| `docs/excluded_instances.md` | Appendix A: why 20 of 706 goals are excluded (→ **686**) |
| `experiments/configs/skip_nontheorems.txt` | Machine-readable skip list (paired with the doc above) |
| `experiments/cases/SOURCES.txt` | Tiny case-study → benchmark path map |
| `prompts_ours_compact/CHANGES.md` | Notes on the compact pack (minimal prompts for simple tests; not paper main) |
| `.env_template` | Full env knobs (API, solvers, PCR/GSE flags) |

Prompt templates under `prompts_ours/`, `prompts_ours_compact/`, `prompts_naive/` are runtime assets, not narrative docs.  
`prompts_ours_compact/` is a **minimal prompt pack for simple tests only** (`--strategy-mode default_simple`); paper runs use `prompts_ours/`.

---

## Method modules

### Base search (LLM4Ind loop)

- Dual templates × N attempts (`MAX_ATTEMPTS_PER_PROMPT`, default 3 → **2N** LLM calls per node)
- Usefulness check + recursive subgoals (`MAX_RECURSION_DEPTH`)
- Entry: `Mate_new.py` (CVC) / `Mate_new_vampire.py` (Vampire)
- Prompts: `prompts_ours/` (`default` / `zero_shot`, paper main); `prompts_naive/` (`naive`); `prompts_ours_compact/` (`default_simple` — **minimal prompts for simple tests only**, not the paper main setting)

### PCR — proof context retrieval

| Piece | Flags / code |
|-------|----------------|
| Lemma library + local harvest | `LEMMA_LIBRARY`, `LEMMA_LIBRARY_LOCAL`, `USEFULNESS_HARVEST_*`, `proof_context_reuse/lemma_harvest.py` |
| Obligation tree | `OBLIGATION_TREE`, `proof_context_reuse/obligation_tree.py` |
| Invalid / soft / unproved memory | `INVALID_LEMMAS` (`off` \| `on` \| `paper`), `UNPROVED_NOT_INVALID` |
| Ancestor path filter + prompt | `ANCESTOR_CYCLE_FILTER`, `ANCESTOR_PROMPT`, `proof_context_reuse/ancestor_stack.py` |
| Static lemma gates | `LEMMA_DEFINED_SYMBOLS`, `LEMMA_FILTER_DROP`, `LEMMA_WELLFORMED_CHECK`, `proof_context_reuse/lemma_gates.py` |

### GSE — guided scheme / structure

| Piece | Flags / code |
|-------|----------------|
| Problem profiler | `PROBLEM_PROFILER`, `PROBLEM_PROFILER_MIN_ATTEMPT`, `PROBLEM_PROFILER_TRIGGER` → `problem_profiler/` |
| Induction scheme | `INDUCTION_SCHEME`, `MODE=both`, `TRIGGER=after_useless`, `NEST=cross_sort`, … → `induction_scheme/` |

Paper GSE gating: inject / run **after a useless attempt**, with profiler **min attempt = 2**.

---

## Main ablation configs

Copy an example, fill keys, then:

```bash
DOTENV_PATH=experiments/configs/<name>.env \
  python3 run_exp_folder.py \
  --root-path ./benchmarks/preprocessed/<suite> \
  --result-dir ./experiments/results \
  --skip-file experiments/configs/skip_nontheorems.txt
```

| Paper name | Template | Meaning |
|------------|----------|---------|
| **PCIS** (Full) | `ablation_pcis.env.example` | PCR on + GSE on |
| **PCR** | `ablation_pcr.env.example` | PCR on only (profiler/scheme off) |
| **GSE** | `ablation_gse.env.example` | Profiler+scheme; PCR off; `INVALID_LEMMAS=paper` |

Shared non-ablation knobs (`LLM_INVALID_*`, child/parse/screen retries): `experiments/configs/shared.env.example` → `shared.env` (gitignored; loaded automatically when present).

Simple / case-study template: `case.env.example` → `case.env` (serial `MAX_PARALLEL_TASKS=1`; default fallback in `env_config.py`).

Vampire: same env + `run_exp_folder_vampire.py` / `Mate_new_vampire.py`.

Full706 chain launchers (CVC5, four suites, `nohup`):
`experiments/scripts/run_ablation_{pcr,gse,pcis}.sh` — see `experiments/scripts/README.md`.

Evaluation size: **706 − 20 = 686** (see `docs/excluded_instances.md`).

---

## Setup

```bash
pip install langchain_openai python-dotenv colorlog psutil tqdm
cp .env_template .env
# or: cp experiments/configs/case.env.example experiments/configs/case.env
# or: cp experiments/configs/ablation_pcis.env.example experiments/configs/ablation_pcis.env
# set OPENAI_API_KEY / OPENAI_API_BASE / OPENAI_MODEL / MODEL_TYPE and solver binaries
```

Solvers expected under `./cvc/...` and `./vampire/vampire` (paths overridable in env).

Optional: `DOTENV_PATH=experiments/configs/ablation_pcis.env` (or `case.env`) overrides the default dotenv load order (`env_config.py`).

---

## Running

**Batch (CVC portfolio):**

```bash
python3 run_exp_folder.py \
  --root-path ./benchmarks/preprocessed/autoproof \
  --result-dir ./experiments/results \
  --skip-file experiments/configs/skip_nontheorems.txt
```

**Batch (Vampire):**

```bash
python3 run_exp_folder_vampire.py \
  --root-path ./benchmarks/preprocessed/autoproof \
  --result-dir ./experiments/results \
  --skip-file experiments/configs/skip_nontheorems.txt
```

| Flag | Meaning |
|------|---------|
| `--root-path` | Preprocessed suite root |
| `--result-dir` | Parent for per-run copies, logs, CSV/JSONL |
| `--skip-file` | Paths to skip (non-theorems) |
| `--baseline` | Solver-only, no LLM |
| `--strategy-mode` | `default` / `zero_shot` (`prompts_ours`, paper main templates); `naive`; `default_simple` (`prompts_ours_compact`, minimal prompts for simple tests only) |

Shell wrappers `run_all_benchmark.sh` / `run_all_benchmark_vampire.sh` loop suites; edit dataset list / log dir inside the script.

**Single task:**

```bash
python3 main.py <task_folder> <base_name>
```

**Preprocess** (only if regenerating from raw SMT-LIB):

```bash
python3 preprocessed.py
```

Preprocessed trees already live under `benchmarks/preprocessed/`.  
Do **not** evaluate `benchmarks/do-not-supported-yet/` (outside the paper suites).

---

## Layout (code)

```
PCIS/
├── Mate_new.py / Mate_new_vampire.py   # recursive prove + LLM loop
├── run_exp_folder*.py                  # multiprocess batch runners
├── main.py                             # single-task entry
├── env_config.py / exp_flags.py        # env + ablation switches
├── proof_context_reuse/                # PCR (library, tree, ancestor, gates)
├── problem_profiler/ / induction_scheme/
├── cvc5_runner.py / vampire_runner.py / solver_profiles.py
├── prompts_ours/                       # paper main templates
├── prompts_ours_compact/               # minimal prompts for simple tests (default_simple)
├── prompts_naive/
├── experiments/configs/                # ablation + case env templates
├── docs/excluded_instances.md
├── benchmarks/preprocessed/            # evaluation suites
└── tests/
```

---

## Models

Any OpenAI-compatible endpoint works via `OPENAI_API_BASE` + `OPENAI_MODEL`.  
`MODEL_TYPE` selects provider-specific wiring in `env_config.py` (e.g. `deepseek-v4-flash`, `qwen3`, `qwen`, `gemini`, `gpt-4o` / `gpt-5`).

Paper-style CVC runs in the ablation templates use DeepSeek-V4-Flash with thinking off; adjust keys/model as needed.

---

## Tests

```bash
pytest tests/ -q
```
