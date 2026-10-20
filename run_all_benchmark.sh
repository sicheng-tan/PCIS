#!/bin/bash

# Log directory (edit as needed)
# LOG_DIR="logs_ours_prompt1x6_depth3"
LOG_DIR="logs_ours_qwen3"

# Create logs directory if missing
mkdir -p "$LOG_DIR"

echo "Starting all benchmark runs - $(date)"
echo "Log files will be saved under $LOG_DIR/"

# Directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Datasets
# declare -a datasets=("autoproof" "dtt")
declare -a datasets=("ind-ben" "vmcai15-dt")

# Run each suite serially
for dataset in "${datasets[@]}"; do
    # Build path from dataset name
    path="$SCRIPT_DIR/benchmarks/preprocessed/$dataset"
    # Per-dataset timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    logfile="$LOG_DIR/${TIMESTAMP}_${dataset}.log"
    
    echo "=========================================="
    echo "Running dataset: $dataset"
    echo "Log file: $logfile"
    echo "Start time: $(date)"
    echo "=========================================="
    
    # Run and tee output to the log file
    # kill all unused processes
    sleep 10
    python3 run_exp_folder.py --root-path "$path" 2>&1 | tee "$logfile"
    # Wait briefly for CVC5 processes to exit
    sleep 10
    ./kill_cvc_processes.sh
    sleep 10
    # Check exit status of the python pipeline stage
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "✓ Dataset $dataset succeeded"
        echo "Succeeded - end time: $(date)" >> "$logfile"
    else
        echo "✗ Dataset $dataset failed"
        echo "Failed - end time: $(date)" >> "$logfile"
        echo "Error: dataset $dataset failed; see log $logfile"
    fi
    
    echo ""
done

echo "=========================================="
echo "All benchmark runs finished - $(date)"
echo "All log files are under $LOG_DIR/"
echo "=========================================="
