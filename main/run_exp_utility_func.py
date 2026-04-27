import os
from pathlib import Path
import time
import subprocess
import threading
import main.config as config
from datetime import datetime
import json
from scipy.io import savemat

def start_artiq_thread_func():
    repo_path = Path(__file__).resolve().parent.parent
    delay_seconds = 0.0  #float(delay_s) if delay_s else 0.0

    if config.package_manager == "conda":
        command = ("conda activate " + config.artiq_environment_name +
                   " && artiq_run " + str(repo_path / "ARTIQ_scripts" / "run_experiment.py"))
        def runner():
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            os.system(command)

    elif config.package_manager == "clang64":
        bat_name = "run_experiment.bat"
        bat_path = repo_path / "experiment_specific_files" / config.which_project / bat_name
        def runner():
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            subprocess.run(["cmd", "/c", str(bat_path)], check=False,
                           creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    else:
        raise RuntimeError(f"Unsupported package manager: {config.package_manager}")

    thread = threading.Thread(target=runner)
    thread.start()
    return thread

def send_int_file_to_artiq_func():
    repo_path = Path(__file__).resolve().parent.parent
    try:
        if config.package_manager == 'conda':
            submit_experiment_thread = threading.Thread(target=os.system, args=['conda activate ' + config.artiq_environment_name + ' && artiq_run ' + str(repo_path / 'ARTIQ_scripts' / 'init_hardware.py')])
        elif config.package_manager == 'clang64':
            submit_experiment_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(repo_path / 'experiment_specific_files' / 'hybrid_experiment' / 'init_hardware.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
        submit_experiment_thread.start()
    except Exception as exc:
        print('Could not execute go_to_edge:', exc)


def delete_run_active_flag_func():
    repo_path = Path(__file__).resolve().parent.parent
    path = Path(repo_path) / 'ARTIQ_scripts' / 'run_active_flag.txt' 
    if path.exists(): 
        path.unlink()

def create_run_active_flag_func():
    repo_path = Path(__file__).resolve().parent.parent
    path = Path(repo_path) / 'ARTIQ_scripts' / 'run_active_flag.txt' 
    try: 
        path.parent.mkdir(parents=True, exist_ok=True) 
        path.touch() 
    except Exception: 
        pass 

def copy_dataset_file_func(column_names, data):
    repo_path = Path(__file__).resolve().parent.parent
    saved_path_info = repo_path / "ARTIQ_scripts" / "saved_path_info.json"

    try:
        with open(saved_path_info, "r") as f:
            path_info = json.load(f)
        experiment_name = path_info.get("experiment_name", "")
        experimental_path = path_info.get("current_run_path", "")
        experimental_metadata_path = path_info.get("current_run_metadata_path", "")
    except Exception as e:
        print(f"Could not read saved_path_info.json: {e}")

    target_directory = Path(experimental_metadata_path) if experimental_metadata_path else (Path(experimental_path) if experimental_path else None)
    if target_directory is None:
        today = datetime.now().strftime('%Y_%m_%d')
        exp_dir = experiment_name if experiment_name else 'unspecified_experiment'
        target_directory = Path(config.experiment_data_root) / exp_dir / today
    try:
        target_directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f'Could not create target directory {target_directory}: {e}')
        
    folder_name = target_directory.name
    folder_date = datetime.now().strftime('%Y%m%d')
    folder_time = folder_name[-8:].replace('_', '') if len(folder_name) >= 8 else datetime.now().strftime('%H%M%S')
    target_file = target_directory / f"dataset_db_copy_{folder_date}_{folder_time}.txt"

    with open(target_file, "w") as f:
        f.write(", ".join(column_names) + "\n")
        f.writelines(f"{entry}\n" for entry in data)