#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO"

ENV_ABS="${DOTENV_PATH:-$REPO/experiments/configs/ablation_gse.env}"
RESULT_DIR="${RESULT_DIR:-$REPO/experiments/results/ablation_gse}"
SKIP_FILE="${SKIP_FILE:-$REPO/experiments/configs/skip_nontheorems.txt}"
LOG_DIR="$RESULT_DIR/logs"
mkdir -p "$LOG_DIR" "$REPO/experiments/results"

STAMP=$(date +%Y%m%d_%H%M%S)
CHAIN_LOG="$REPO/experiments/results/full706_chain_${STAMP}_ablation_gse.log"
PIDFILE="$LOG_DIR/master.pid"
MASTER="$LOG_DIR/${STAMP}_master.log"
TAG="ablation_gse"

if [[ ! -f "$ENV_ABS" ]]; then
  echo "ERROR: missing $ENV_ABS" >&2
  echo "  cp experiments/configs/ablation_gse.env.example experiments/configs/ablation_gse.env" >&2
  exit 1
fi
if [[ ! -f "$SKIP_FILE" ]]; then
  echo "ERROR: missing skip file $SKIP_FILE" >&2
  exit 1
fi

if pgrep -af "$TAG" | grep -vE "pgrep|$(basename "$0")" >/dev/null 2>&1; then
  echo "ERROR: leftover processes still match $TAG; abort." >&2
  pgrep -af "$TAG" || true
  exit 1
fi
if [[ -d "$RESULT_DIR" ]] && [[ -n "$(ls -A "$RESULT_DIR" 2>/dev/null | grep -v '^logs$' || true)" ]]; then
  echo "ERROR: $RESULT_DIR is not empty (besides logs). Clean it first." >&2
  ls -la "$RESULT_DIR" >&2
  exit 1
fi

nohup env \
  REPO="$REPO" \
  DOTENV_PATH="$ENV_ABS" \
  RESULT_DIR="$RESULT_DIR" \
  LOG_DIR="$LOG_DIR" \
  MASTER="$MASTER" \
  SKIP_FILE="$SKIP_FILE" \
  bash -c '
set -uo pipefail
cd "$REPO"
export DOTENV_PATH
{
  echo "START $(date)"
  echo "REPO=$REPO"
  echo "DOTENV_PATH=$DOTENV_PATH"
  echo "RESULT_DIR=$RESULT_DIR"
  echo "SKIP_FILE=$SKIP_FILE"
  echo "STRATEGY_MODE=default"
  echo "ABLATION=GSE"
  for key in ENABLE_THINKING MODEL_TYPE OPENAI_MODEL \
    LEMMA_LIBRARY OBLIGATION_TREE INVALID_LEMMAS LEMMA_LIBRARY_LOCAL \
    ANCESTOR_PROMPT ANCESTOR_CYCLE_FILTER UNPROVED_NOT_INVALID \
    PROBLEM_PROFILER PROBLEM_PROFILER_MIN_ATTEMPT PROBLEM_PROFILER_TRIGGER \
    INDUCTION_SCHEME INDUCTION_SCHEME_MODE INDUCTION_SCHEME_TRIGGER \
    INDUCTION_SCHEME_GOAL_GATE INDUCTION_SCHEME_PROMPT INDUCTION_SCHEME_NEST \
    LLM_INVALID_ONLY_STOP LLM_INVALID_CE_VERIFY CHILD_LLM_ATTEMPTS \
    LLM_SCREEN_RETRIES LEMMA_WELLFORMED_CHECK ROOT_FINISH_PROVE_TIMEOUT \
    MAX_PARALLEL_TASKS SKIP_PROBLEMS_FILE
  do
    echo "$(grep -E "^${key}=" "$DOTENV_PATH" || echo "${key}=(unset)")"
  done
} | tee "$MASTER"

fail=0
for dataset in autoproof dtt ind-ben vmcai15-dt; do
  path="./benchmarks/preprocessed/$dataset"
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  logfile="$LOG_DIR/${TIMESTAMP}_${dataset}.log"
  echo "==========================================" | tee -a "$MASTER"
  echo "dataset=$dataset start=$(date)" | tee -a "$MASTER"
  python3 run_exp_folder.py \
    --strategy-mode=default \
    --root-path "$path" \
    --result-dir "$RESULT_DIR" \
    --skip-file "$SKIP_FILE" \
    2>&1 | tee "$logfile"
  status=${PIPESTATUS[0]}
  echo "dataset=$dataset status=$status end=$(date)" | tee -a "$MASTER"
  if [ "$status" -ne 0 ]; then fail=1; fi
done
echo "ALL_DONE $(date) fail=$fail" | tee -a "$MASTER"
exit $fail
' > "$CHAIN_LOG" 2>&1 &

CHAIN_PID=$!
echo "$CHAIN_PID" > "$PIDFILE"
echo "launched PID=$CHAIN_PID"
echo "PIDFILE=$PIDFILE"
echo "CHAIN_LOG=$CHAIN_LOG"
echo "MASTER=$MASTER"
echo "RESULT_DIR=$RESULT_DIR"
echo "DOTENV_PATH=$ENV_ABS"
sleep 4
if kill -0 "$CHAIN_PID" 2>/dev/null; then
  echo "process_alive=yes"
else
  echo "ERROR: process_alive=no; see $CHAIN_LOG" >&2
  tail -40 "$CHAIN_LOG" >&2 || true
  exit 1
fi
