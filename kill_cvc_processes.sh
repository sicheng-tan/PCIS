#!/bin/bash

# Kill all cvc4 and cvc5 processes
# Loops until no cvc4/cvc5 processes remain

echo "Killing all cvc4 and cvc5 processes..."

while true; do
    # Collect cvc4 / cvc5 PIDs
    pids=$(ps aux | grep -E 'cvc[45]' | grep -v grep | grep -v kill_cvc5.sh | awk '{print $2}')
    
    if [ -z "$pids" ]; then
        echo "No cvc4 or cvc5 processes found; done."
        break
    else
        echo "Found $(echo $pids | wc -w) cvc4/cvc5 process(es); terminating..."
        # Kill all matches
        echo $pids | xargs kill -9 2>/dev/null
        echo "Signals sent; rechecking in 2 seconds..."
        sleep 2
    fi
done

echo "All cvc4 and cvc5 processes have been terminated."
