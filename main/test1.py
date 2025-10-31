import os
from pathlib import Path

repo_path = Path(__file__).resolve().parent.parent


file_name = "led.py"

path_ = repo_path / "ARTIQ_scripts" / file_name
print(str(path_))
if not os.path.exists(path_):
    with open(path_, 'w'): pass
print(2)

submit_experiment_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'run_experiment.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
                
with open('../logs/metadata.json', "w") as outfile:
    json.dump(to_dict(self.experiment),outfile,indent=4)

submit_experiment_thread.start()