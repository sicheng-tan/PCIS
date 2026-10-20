#!/bin/bash

# Kill all vampire processes
# Loops until no vampire processes remain

echo "Killing all vampire processes..."

# This script's PID (excluded from matches)
SCRIPT_PID=$$

while true; do
    # Collect vampire PIDs
    # Match real vampire executables; exclude:
    # 1. the grep process itself
    # 2. kill_vampire_processes.sh
    # 3. unrelated SCREEN sessions
    # 4. this script
    pids=$(ps aux | grep -E '[^/]vampire[^/]|/vampire/vampire|vampire\.smt2' | \
           grep -v grep | \
           grep -v 'kill_vampire' | \
           grep -v 'SCREEN' | \
           grep -v "$$" | \
           awk '{print $2}')
    
    if [ -z "$pids" ]; then
        echo "No vampire processes found; done."
        break
    else
        count=$(echo $pids | wc -w)
        echo "Found $count vampire process(es); terminating..."
        
        # Try graceful termination first
        for pid in $pids; do
            # Skip if the process already exited
            if ps -p $pid > /dev/null 2>&1; then
                # Prefer killing the process group
                kill -TERM -$pid 2>/dev/null || kill -TERM $pid 2>/dev/null
            fi
        done
        
        # Wait for exit
        sleep 2
        
        # Force-kill any survivors
        remaining_pids=$(ps aux | grep -E '[^/]vampire[^/]|/vampire/vampire|vampire\.smt2' | \
                         grep -v grep | \
                         grep -v 'kill_vampire' | \
                         grep -v 'SCREEN' | \
                         grep -v "$$" | \
                         awk '{print $2}')
        
        if [ -n "$remaining_pids" ]; then
            echo "Force-killing remaining processes..."
            echo $remaining_pids | xargs kill -9 2>/dev/null
        fi
        
        echo "Signals sent; rechecking in 2 seconds..."
        sleep 2
    fi
done

echo "All vampire processes have been terminated."
