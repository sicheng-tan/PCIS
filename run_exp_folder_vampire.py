#!/usr/bin/env python3
import os
import sys
import logging
import time
import signal
import multiprocessing
import shutil
import psutil
import argparse
from datetime import datetime
from tempfile import template
from tqdm import tqdm
import contextlib
import io
from concurrent.futures import ProcessPoolExecutor, as_completed
import Mate_new_vampire as mate_solver
from env_config import setup_environment
from exp_stats import (
    ensure_task_summary,
    log_run_config,
    print_batch_stats,
    write_results_csv,
)
from skip_problems import (
    add_skip_file_argument,
    filter_skipped_folders,
    report_skipped_folders,
    resolve_skip_file,
)
prove_run = mate_solver.prove_run

# Load configuration
config = setup_environment()

# setup_task_logger removed; each process configures logging independently

class TaskTimeoutError(Exception):
    """Task timeout exception."""
    pass

def timeout_handler(signum, frame):
    """Timeout signal handler."""
    raise TaskTimeoutError("Task execution timed out")

def cleanup_process_tree(pid):
    """Terminate a process and all of its children."""
    try:
        if psutil.pid_exists(pid):
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # First try to terminate all children gracefully
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # Wait briefly for graceful exit
            gone, alive = psutil.wait_procs(children, timeout=3)
            
            # Force-kill processes still alive
            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # Finally terminate the parent process
            try:
                parent.terminate()
                parent.wait(timeout=3)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    parent.kill()
                except psutil.NoSuchProcess:
                    pass
                    
            logging.debug(f"Cleaned process tree PID: {pid}")
    except Exception as e:
        logging.error(f"Failed to clean process tree PID: {pid}, error: {e}")

def run_task_with_timeout(folder, template_name, task_timeout, result_queue, strategy_mode, baseline_mode=None):
    """Run a task inside an isolated process."""
    try:
        # Build log filename (named by start time)
        start_datetime = datetime.now()
        log_filename = start_datetime.strftime("%Y%m%d_%H%M%S.log")
        log_filepath = os.path.join(folder, log_filename)
        
        # Configure logger: console and file
        import logging
        
        # Configure the root logger because Mate_new.py uses the root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Clear existing handlers
        root_logger.setLevel(logging.INFO)
        
        # Add file handler to root logger
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                         datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Add console handler to root logger
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                            datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Run prove_run
        start_time = time.time()
        # Baseline mode is controlled only by CLI args
        actual_baseline_mode = baseline_mode if baseline_mode is not None else False
        
        if actual_baseline_mode:
            logging.info(f"Baseline mode: starting task: {os.path.basename(folder)}, timeout: {task_timeout}s")
        else:
            logging.info(f"Starting task: {os.path.basename(folder)}, strategy: {strategy_mode}, timeout: {task_timeout}s")
        log_run_config(
            backend="vampire",
            strategy_mode=strategy_mode,
            baseline=actual_baseline_mode,
            task_timeout=task_timeout,
            extra={"task": os.path.basename(folder)},
        )
        final_status = prove_run(folder, template_name, 0, strategy_mode=strategy_mode, baseline_only=actual_baseline_mode)
        end_time = time.time()
        
        # Close handlers
        file_handler.close()
        root_logger.removeHandler(file_handler)
        root_logger.removeHandler(console_handler)
        
        # Put result on the queue
        result_queue.put((folder, final_status, end_time - start_time, None))
        
    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        # Put error result on the queue
        result_queue.put((folder, False, elapsed_time, str(e)))

def process_single_task(task_info):
    """Handle one task under multiprocessing with process-level timeout."""
    folder, template_name, strategy_mode, baseline_mode = task_info
    task_timeout = config['TASK_TIMEOUT']
    
    # Create IPC queue
    result_queue = multiprocessing.Queue()
    
    # Spawn child process for the task
    process = multiprocessing.Process(
        target=run_task_with_timeout,
        args=(folder, template_name, task_timeout, result_queue, strategy_mode, baseline_mode)
    )
    
    start_time = time.time()
    process.start()
    
    try:
        # Wait for process completion or timeout
        process.join(timeout=task_timeout)
        
        if process.is_alive():
            # Process timed out; force-kill the whole process tree
            logging.warning(f"Task timed out; force-killing process tree: {os.path.basename(folder)}")
            cleanup_process_tree(process.pid)
            process.join(timeout=5)  # Give the process 5s to exit gracefully
            
            if process.is_alive():
                # If still alive, force-kill
                process.kill()
                process.join()
            
            elapsed_time = time.time() - start_time
            return folder, False, elapsed_time, f"Task timeout ({task_timeout}s)"
        
        # Process finished normally; fetch result
        if not result_queue.empty():
            return result_queue.get()
        else:
            # Process finished with no result; likely abnormal exit
            elapsed_time = time.time() - start_time
            return folder, False, elapsed_time, "Process exited abnormally with no return value"
            
    except Exception as e:
        # Handle exceptions
        if process.is_alive():
            cleanup_process_tree(process.pid)
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()
        
        elapsed_time = time.time() - start_time
        return folder, False, elapsed_time, f"Process management error: {str(e)}"

def find_template_folders(root_path, template_name="template.smt2"):
    """Recursively find folders that contain template.smt2."""
    template_folders = []
    
    for root, dirs, files in os.walk(root_path):
        if template_name in files:
            template_folders.append(root)
    
    return sorted(template_folders)

def copy_folder_for_experiment(original_path, dest_parent=None):
    """
    Copy the original folder into a timestamped directory under the results parent.
    dest_parent defaults to result_files under the project root.
    Returns the new folder path.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    result_files_dir = dest_parent or os.path.join(script_dir, "result_files")
    os.makedirs(result_files_dir, exist_ok=True)

    original_folder_name = os.path.basename(original_path.rstrip(os.sep))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_folder_name = f"{timestamp}_{original_folder_name}"
    new_folder_path = os.path.join(result_files_dir, new_folder_name)

    print(f"Copying folder: {original_path} -> {new_folder_path}")
    shutil.copytree(original_path, new_folder_path)
    print(f"Folder copy complete: {new_folder_path}")

    return new_folder_path

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='ProofMate experiment runner')
    parser.add_argument('--baseline', action='store_true', 
                       help='Enable baseline mode (initial verification only)')
    parser.add_argument('--root-path', type=str,
                       default="./benchmarks/preprocessed/autoproof",
                       help='Path to the original problem folder '
                            '(default: ./benchmarks/preprocessed/autoproof)')
    parser.add_argument('--strategy-mode', type=str, 
                       choices=['default', 'default_simple', 'zero_shot', 'naive'],
                       default='default',
                       help='Prompt pack: default uses prompts_ours (equality+rewrite, N each); '
                            'default_simple uses prompts_ours_compact (same two templates, compact system); '
                            'zero_shot same as default; '
                            'naive uses only prompt_naive repeated 2N times')
    parser.add_argument('--result-dir', type=str, default=None,
                       help='Results parent for this run (copied problems, logs, CSV). '
                            'If omitted, copies go under result_files/ and CSV under result_csv/')
    add_skip_file_argument(parser)
    args = parser.parse_args()

    # Set multiprocessing start method (required on some systems)
    multiprocessing.set_start_method('spawn', force=True)
    original_root_path = args.root_path
    result_parent = os.path.abspath(args.result_dir) if args.result_dir else None

    # Copy folder to avoid modifying originals
    root_path = copy_folder_for_experiment(original_root_path, dest_parent=result_parent)

    template_name = "template"
    folders = find_template_folders(root_path, template_name + ".smt2")
    found = len(folders)
    skip_file = resolve_skip_file(args.skip_file)
    folders, skipped, _patterns = filter_skipped_folders(folders, skip_file)
    print(f"Found {found} tasks to solve")
    if skip_file:
        report_skipped_folders(skipped, skip_file)
        print(f"{len(folders)} tasks remaining after exclusions")
    
    # Show run mode
    if args.baseline:
        print("Run mode: Baseline (initial verification only)")
    else:
        print(f"Run mode: Full (includes LLM lemma generation)")
        print(f"Strategy mode: {args.strategy_mode}")
        if args.strategy_mode == "naive":
            print("   naive: only prompt_naive, repeated 2×MAX_ATTEMPTS_PER_PROMPT (no template selection)")
        elif args.strategy_mode == "default_simple":
            print("   default_simple: same two templates as default; system from prompts_ours_compact")
    
    # Store all results
    results = []
    total_start_time = time.time()
    
    # Build task list including baseline and strategy-mode args
    task_list = [(folder, template_name, args.strategy_mode, args.baseline) for folder in folders]
    
    # Run with a process pool, up to MAX_PARALLEL_TASKS workers
    max_parallel_tasks = config['MAX_PARALLEL_TASKS']
    unsat_count = 0
    total_tasks = len(folders)
    if folders:
        max_workers = min(max_parallel_tasks, len(folders), multiprocessing.cpu_count())
        print(f"Using {max_workers} parallel processes for {len(folders)} tasks")
        with tqdm(total=len(folders), desc=f"Processing tasks (unsat: {unsat_count}/{total_tasks})", unit="task") as pbar:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_folder = {executor.submit(process_single_task, task): task[0] 
                                  for task in task_list}
                
                # Collect results
                for future in as_completed(future_to_folder):
                    folder_path = future_to_folder[future]
                    try:
                        folder, final_status, duration, error = future.result()
                        
                        if error:
                            print(f"\nTask error: {os.path.basename(folder)} - error: {error}")
                            ensure_task_summary(folder, proved=False, error=str(error))
                            results.append((folder, False, duration, error))
                        else:
                            results.append((folder, final_status, duration, None))
                            
                            # If result is unsat, update the counter
                            if final_status:
                                unsat_count += 1
                            
                            # Print task completion feedback
                            result_text = "unsat" if final_status else "failed"
                            print(f"\nTask done: {os.path.basename(folder)} - {result_text} - time: {duration:.2f}s")
                            
                    except Exception as e:
                        print(f"\nTask error: {os.path.basename(folder_path)} - error: {str(e)}")
                        try:
                            ensure_task_summary(folder_path, proved=False, error=str(e))
                        except Exception:
                            pass
                        results.append((folder_path, False, -1, str(e)))
                    
                    # Update progress-bar description
                    pbar.set_description(f"Processing tasks (unsat: {unsat_count}/{total_tasks})")
                    pbar.update(1)
    else:
        print("No tasks to solve (possibly all excluded by skip-file)")
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Generate CSV report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Extract dataset name (last component of root-path)
    dataset_name = os.path.basename(os.path.normpath(original_root_path))
    if args.baseline:
        csv_filename = f"results_{timestamp}_{dataset_name}_baseline.csv"
    else:
        csv_filename = f"results_{timestamp}_{dataset_name}_{args.strategy_mode}.csv"
    
    if result_parent:
        result_csv_dir = root_path
    else:
        result_csv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result_csv")
    os.makedirs(result_csv_dir, exist_ok=True)

    csv_filepath = os.path.join(result_csv_dir, csv_filename)
    jsonl_filepath = write_results_csv(results, csv_filepath, original_root_path)
    
    print_batch_stats(results, total_duration)
    print(f"Results saved to: {csv_filepath}")
    print(f"Detailed summary saved to: {jsonl_filepath}")