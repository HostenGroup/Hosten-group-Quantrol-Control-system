'''
File I/O operations for Quantrol experimental sequences.

This module handles saving and loading experiment sequences, default settings,
and managing file paths and pickled data.

Author  :   Vyacheslav Li (until 2.0), Andrea Pupic, Alexei Gurchenko (later versions)
Email   :   vyacheslav.li.1991@gmail.com, andrea.pupic@ist.ac.at, alexei.gurchenko@ist.ac.at
Date    :   07.30.2024 (2.0)
Update  :   11.2025 
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''

import pickle
from pathlib import Path
from typing import Optional, Tuple
from copy import deepcopy


def save_experiment(experiment, file_path: str = None) -> Tuple[bool, str, Optional[str]]:
    '''
    Save an experiment object to a file using pickle.
    
    Args:
        experiment: The Experiment object to save
        file_path: Optional path to save to. If None, uses experiment.file_name
        
    Returns:
        Tuple of (success: bool, message: str, saved_path: Optional[str])
    '''
    if file_path is None:
        file_path = experiment.file_name
        
    if not file_path:
        return (False, "No file path specified", None)
    
    try:
        with open(file_path, 'wb') as file:
            pickle.dump(experiment, file)
        return (True, f"Sequence saved at {file_path}", file_path)
    except Exception as e:
        return (False, f"Saving failed: {e}", None)


def load_experiment(file_path: str) -> Tuple[bool, str, Optional[object]]:
    '''
    Load an experiment object from a pickled file.
    
    Args:
        file_path: Path to the file to load
        
    Returns:
        Tuple of (success: bool, message: str, experiment: Optional[Experiment])
    '''
    if not file_path:
        return (False, "No file selected", None)
    
    try:
        with open(file_path, 'rb') as file:
            experiment = pickle.load(file)
        return (True, f"Sequence loaded from {file_path}", experiment)
    except Exception as e:
        return (False, f"Could not load the file: {e}", None)


def ensure_backward_compatibility(experiment) -> list:
    '''
    Ensure backward compatibility by adding missing attributes to loaded experiments.
    
    Args:
        experiment: The loaded Experiment object
        
    Returns:
        List of compatibility notes about what was added/fixed
    '''
    notes = []
    
    # Add skip_images attribute if missing (old versions)
    if not hasattr(experiment, 'skip_images'):
        experiment.skip_images = False
        notes.append("Added skip_images attribute")
    
    # Add cam_trigger_off attribute if missing
    if not hasattr(experiment, 'cam_trigger_off'):
        experiment.cam_trigger_off = False
        notes.append("Added cam_trigger_off attribute")
    
    # Add cont_run_after_exp attribute if missing
    if not hasattr(experiment, 'cont_run_after_exp'):
        experiment.cont_run_after_exp = False
        notes.append("Added cont_run_after_exp attribute")
    
    # Add camera_enabled attribute if missing
    if not hasattr(experiment, 'camera_enabled'):
        experiment.camera_enabled = False
        notes.append("Added camera_enabled attribute")
    
    # Add texp_locked attribute if missing
    if not hasattr(experiment, 'texp_locked'):
        experiment.texp_locked = False
        notes.append("Added texp_locked attribute")
    
    return notes


def save_default_settings(experiment, repo_path: Path) -> Tuple[bool, str]:
    '''
    Save the default edge and channel titles to the default settings file.
    
    Args:
        experiment: The Experiment object with default settings
        repo_path: Path to the repository root
        
    Returns:
        Tuple of (success: bool, message: str)
    '''
    default_path = repo_path / "default" / "default"
    
    try:
        # Create default directory if it doesn't exist
        default_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(default_path, 'wb') as file:
            pickle.dump(experiment, file)
        return (True, f"Default settings saved to {default_path}")
    except Exception as e:
        return (False, f"Could not save default settings: {e}")


def load_default_settings(repo_path: Path) -> Tuple[bool, str, Optional[object]]:
    '''
    Load default edge and channel titles from the default settings file.
    
    Args:
        repo_path: Path to the repository root
        
    Returns:
        Tuple of (success: bool, message: str, default_experiment: Optional[Experiment])
    '''
    default_path = repo_path / "default" / "default"
    
    try:
        with open(default_path, 'rb') as file:
            default_experiment = pickle.load(file)
        return (True, "Default values loaded", default_experiment)
    except Exception as e:
        return (False, f"Could not load default settings: {e}", None)


def get_default_directory(repo_path: Path) -> Path:
    '''
    Get the default directory path for saving/loading sequences.
    
    Args:
        repo_path: Path to the repository root
        
    Returns:
        Path to the sequences directory
    '''
    sequences_dir = repo_path / "sequences"
    sequences_dir.mkdir(exist_ok=True)
    return sequences_dir


def apply_default_to_experiment(experiment, default_experiment) -> None:
    '''
    Apply default settings from default_experiment to the current experiment.
    
    Args:
        experiment: The current Experiment object to update
        default_experiment: The default Experiment object with settings to apply
    '''
    # Reassign the default values
    experiment.sequence[0] = deepcopy(default_experiment.sequence[0])
    experiment.title_digital_tab = deepcopy(default_experiment.title_digital_tab)
    experiment.title_analog_tab = deepcopy(default_experiment.title_analog_tab)
    experiment.title_dds_tab = deepcopy(default_experiment.title_dds_tab)
    
    # Add other title tabs if they exist in the default
    if hasattr(default_experiment, 'title_mirny_tab'):
        experiment.title_mirny_tab = deepcopy(default_experiment.title_mirny_tab)
    if hasattr(default_experiment, 'title_sampler_tab'):
        experiment.title_sampler_tab = deepcopy(default_experiment.title_sampler_tab)
    if hasattr(default_experiment, 'title_slow_dds_tab'):
        experiment.title_slow_dds_tab = deepcopy(default_experiment.title_slow_dds_tab)


def prepare_experiment_for_save(experiment, camera_box=None, texp_locked=None) -> None:
    '''
    Prepare experiment object for saving by capturing current UI state.
    
    Args:
        experiment: The Experiment object to prepare
        camera_box: Optional QCheckBox for camera enabled state
        texp_locked: Optional boolean for exposure time lock state
    '''
    if camera_box is not None:
        experiment.camera_enabled = camera_box.isChecked()
    if texp_locked is not None:
        experiment.texp_locked = texp_locked


def get_experiment_selection_id(experiment) -> Optional[int]:
    '''
    Get the experiment ID from experimental data for restoring selection.
    
    Args:
        experiment: The Experiment object
        
    Returns:
        Integer experiment ID or None if not found/invalid
    '''
    try:
        exp_data = getattr(experiment, "experimental_data", None)
        row = getattr(exp_data, "experiment_id", None) if exp_data else None
        
        if isinstance(row, int):
            return row
        elif isinstance(row, str):
            row_stripped = row.strip()
            if row_stripped.isdigit():
                return int(row_stripped)
    except:
        pass
    
    return None
