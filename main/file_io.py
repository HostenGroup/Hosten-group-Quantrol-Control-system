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
from data_structures import ExperimentalData, Camera, LiveCamera
import config


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

    # Add live_camera_enabled attribute if missing
    if not hasattr(experiment, 'live_camera_enabled'):
        experiment.live_camera_enabled = False
        notes.append("Added live_camera_enabled attribute")
    
    # Add texp_locked attribute if missing
    if not hasattr(experiment, 'texp_locked'):
        experiment.texp_locked = False
        notes.append("Added texp_locked attribute")

    # Ensure experimental_data and camera/live_camera payloads exist
    if not hasattr(experiment, 'experimental_data') or experiment.experimental_data is None:
        experiment.experimental_data = ExperimentalData()
        notes.append("Added experimental_data attribute")
    if not hasattr(experiment.experimental_data, 'camera') or experiment.experimental_data.camera is None:
        experiment.experimental_data.camera = Camera()
        notes.append("Added experimental_data.camera attribute")
    if not hasattr(experiment.experimental_data.camera, 'roi_enabled'):
        experiment.experimental_data.camera.roi_enabled = False
    if not hasattr(experiment.experimental_data.camera, 'roi_x_center'):
        experiment.experimental_data.camera.roi_x_center = None
    if not hasattr(experiment.experimental_data.camera, 'roi_y_center'):
        experiment.experimental_data.camera.roi_y_center = None
    if not hasattr(experiment.experimental_data.camera, 'roi_width'):
        experiment.experimental_data.camera.roi_width = None
    if not hasattr(experiment.experimental_data.camera, 'roi_height'):
        experiment.experimental_data.camera.roi_height = None
    if not hasattr(experiment.experimental_data, 'live_cameras') or experiment.experimental_data.live_cameras is None:
        experiment.experimental_data.live_cameras = [LiveCamera(), LiveCamera()]
        notes.append("Added experimental_data.live_cameras attribute")
    else:
        try:
            experiment.experimental_data.live_cameras = experiment.experimental_data.live_cameras
        except Exception:
            experiment.experimental_data.live_cameras = [LiveCamera(), LiveCamera()]
            notes.append("Normalized experimental_data.live_cameras attribute")

    if not hasattr(experiment.experimental_data, 'live_camera') or experiment.experimental_data.live_camera is None:
        experiment.experimental_data.live_camera = LiveCamera()
        notes.append("Added experimental_data.live_camera attribute")

    live_camera = experiment.experimental_data.live_camera
    live_cameras = experiment.experimental_data.live_cameras
    if not hasattr(live_camera, 'enabled'):
        live_camera.enabled = bool(getattr(experiment, 'live_camera_enabled', False))
        notes.append("Added live_camera.enabled attribute")
    if not hasattr(live_camera, 'camera_name'):
        live_camera.camera_name = None
        notes.append("Added live_camera.camera_name attribute")
    if not hasattr(live_camera, 'serial_number'):
        live_camera.serial_number = None
        notes.append("Added live_camera.serial_number attribute")
    if not hasattr(live_camera, 'gain_db'):
        live_camera.gain_db = None
        notes.append("Added live_camera.gain_db attribute")
    if not hasattr(live_camera, 'exposure_time_ms'):
        live_camera.exposure_time_ms = None
        notes.append("Added live_camera.exposure_time_ms attribute")
    if not hasattr(live_camera, 'format_name'):
        live_camera.format_name = None
        notes.append("Added live_camera.format_name attribute")
    if not hasattr(live_camera, 'hardware_trigger'):
        live_camera.hardware_trigger = False
        notes.append("Added live_camera.hardware_trigger attribute")
    if not hasattr(live_camera, 'subtraction_enabled'):
        live_camera.subtraction_enabled = False
        notes.append("Added live_camera.subtraction_enabled attribute")
    if not hasattr(live_camera, 'dynamic_subtraction_enabled'):
        live_camera.dynamic_subtraction_enabled = False
        notes.append("Added live_camera.dynamic_subtraction_enabled attribute")
    if not hasattr(live_camera, 'gaussian_enabled'):
        live_camera.gaussian_enabled = False
        notes.append("Added live_camera.gaussian_enabled attribute")
    if not hasattr(live_camera, 'gaussian_sigma'):
        live_camera.gaussian_sigma = 1.0
        notes.append("Added live_camera.gaussian_sigma attribute")
    if not hasattr(live_camera, 'gaussian_kernel'):
        live_camera.gaussian_kernel = 5
        notes.append("Added live_camera.gaussian_kernel attribute")
    if not hasattr(live_camera, 'display_gain'):
        live_camera.display_gain = 0.0
        notes.append("Added live_camera.display_gain attribute")
    if not hasattr(live_camera, 'downsample_factor'):
        live_camera.downsample_factor = 2.0
        notes.append("Added live_camera.downsample_factor attribute")
    if not hasattr(live_camera, 'fps_limit_enabled'):
        live_camera.fps_limit_enabled = False
        notes.append("Added live_camera.fps_limit_enabled attribute")
    if not hasattr(live_camera, 'target_fps'):
        live_camera.target_fps = 12.0
        notes.append("Added live_camera.target_fps attribute")
    if not hasattr(live_camera, 'roi_enabled'):
        live_camera.roi_enabled = False
        notes.append("Added live_camera.roi_enabled attribute")
    if not hasattr(live_camera, 'roi_x_center'):
        live_camera.roi_x_center = None
        notes.append("Added live_camera.roi_x_center attribute")
    if not hasattr(live_camera, 'roi_y_center'):
        live_camera.roi_y_center = None
        notes.append("Added live_camera.roi_y_center attribute")
    if not hasattr(live_camera, 'roi_width'):
        live_camera.roi_width = None
        notes.append("Added live_camera.roi_width attribute")
    if not hasattr(live_camera, 'roi_height'):
        live_camera.roi_height = None
        notes.append("Added live_camera.roi_height attribute")
    if not hasattr(live_camera, 'zoom_on_roi'):
        live_camera.zoom_on_roi = False
        notes.append("Added live_camera.zoom_on_roi attribute")

    if len(live_cameras) < 2:
        live_cameras = list(live_cameras) + [LiveCamera() for _ in range(2 - len(live_cameras))]
        experiment.experimental_data.live_cameras = live_cameras
        notes.append("Expanded live camera slots to two entries")

    for slot_index, slot_camera in enumerate(live_cameras[:2]):
        if slot_camera is None:
            live_cameras[slot_index] = LiveCamera()
            continue
        if not hasattr(slot_camera, 'enabled'):
            slot_camera.enabled = bool(getattr(experiment, 'live_camera_enabled', False))
        if not hasattr(slot_camera, 'camera_name'):
            slot_camera.camera_name = None
        if not hasattr(slot_camera, 'serial_number'):
            slot_camera.serial_number = None
        if not hasattr(slot_camera, 'gain_db'):
            slot_camera.gain_db = None
        if not hasattr(slot_camera, 'exposure_time_ms'):
            slot_camera.exposure_time_ms = None
        if not hasattr(slot_camera, 'format_name'):
            slot_camera.format_name = None
        if not hasattr(slot_camera, 'hardware_trigger'):
            slot_camera.hardware_trigger = False
        if not hasattr(slot_camera, 'subtraction_enabled'):
            slot_camera.subtraction_enabled = False
        if not hasattr(slot_camera, 'dynamic_subtraction_enabled'):
            slot_camera.dynamic_subtraction_enabled = False
        if not hasattr(slot_camera, 'gaussian_enabled'):
            slot_camera.gaussian_enabled = False
        if not hasattr(slot_camera, 'gaussian_sigma'):
            slot_camera.gaussian_sigma = 1.0
        if not hasattr(slot_camera, 'gaussian_kernel'):
            slot_camera.gaussian_kernel = 5
        if not hasattr(slot_camera, 'display_gain'):
            slot_camera.display_gain = 0.0
        if not hasattr(slot_camera, 'downsample_factor'):
            slot_camera.downsample_factor = 2.0
        if not hasattr(slot_camera, 'fps_limit_enabled'):
            slot_camera.fps_limit_enabled = False
        if not hasattr(slot_camera, 'target_fps'):
            slot_camera.target_fps = 12.0
        if not hasattr(slot_camera, 'roi_enabled'):
            slot_camera.roi_enabled = False
        if not hasattr(slot_camera, 'roi_x_center'):
            slot_camera.roi_x_center = None
        if not hasattr(slot_camera, 'roi_y_center'):
            slot_camera.roi_y_center = None
        if not hasattr(slot_camera, 'roi_width'):
            slot_camera.roi_width = None
        if not hasattr(slot_camera, 'roi_height'):
            slot_camera.roi_height = None
        if not hasattr(slot_camera, 'zoom_on_roi'):
            slot_camera.zoom_on_roi = False
    # Add save_sampled_variables attribute if missing
    if not hasattr(experiment, 'save_sampled_variables'):
        experiment.save_sampled_variables = False
        notes.append("Added save_sampled_variables attribute")
    
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
    sequences_dir = repo_path / 'experiment_specific_files' / config.which_project / "sequences"
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


def prepare_experiment_for_save(experiment, camera_box=None, texp_locked=None, live_camera_box=None, save_sampled_box=None) -> None:
    '''
    Prepare experiment object for saving by capturing current UI state.
    
    Args:
        experiment: The Experiment object to prepare
        camera_box: Optional QCheckBox for camera enabled state
        texp_locked: Optional boolean for exposure time lock state
    '''
    if camera_box is not None:
        experiment.camera_enabled = camera_box.isChecked()
    if live_camera_box is not None:
        experiment.live_camera_enabled = live_camera_box.isChecked()
        if hasattr(experiment, "experimental_data") and experiment.experimental_data is not None:
            if hasattr(experiment.experimental_data, "live_camera") and experiment.experimental_data.live_camera is not None:
                experiment.experimental_data.live_camera.enabled = bool(experiment.live_camera_enabled)
    if save_sampled_box is not None:
        try:
            experiment.save_sampled_variables = bool(save_sampled_box.isChecked())
        except Exception:
            experiment.save_sampled_variables = False
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


def load_pending_log_entries(repo_path: Path, cache_dict: dict = None) -> list:
    """
    Retrieve any deferred experiment log entries from disk into memory.
    
    Args:
        repo_path: Path to the repository root
        cache_dict: Optional dictionary with '_pending_log_entries_cache' key for caching
        
    Returns:
        List of pending log entry dictionaries
    """
    if cache_dict is not None and "_pending_log_entries_cache" in cache_dict:
        cached_value = cache_dict["_pending_log_entries_cache"]
        if cached_value is not None:
            return list(cached_value)

    path = repo_path / "logs" / "pending_experiment_log_entries.json"
    entries = []
    if path.exists():
        try:
            import json
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, list):
                    entries = data
        except Exception:
            # Silently fail - caller should handle logging
            pass
    
    if cache_dict is not None:
        cache_dict["_pending_log_entries_cache"] = entries
    return list(entries)


def set_pending_log_entries(repo_path: Path, entries: list, cache_dict: dict = None) -> Optional[str]:
    """
    Persist the supplied pending log entries and refresh the cache.
    
    Args:
        repo_path: Path to the repository root
        entries: List of entry dictionaries to persist
        cache_dict: Optional dictionary with '_pending_log_entries_cache' key for caching
        
    Returns:
        Error message string if failed, None if successful
    """
    import json
    
    entries_list = list(entries)
    if cache_dict is not None:
        cache_dict["_pending_log_entries_cache"] = entries_list
    
    path = repo_path / "logs" / "pending_experiment_log_entries.json"
    try:
        if entries_list:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(entries_list, handle, indent=2)
        else:
            if path.exists():
                path.unlink()
        return None
    except Exception as exc:
        return f"Could not update pending experiment log file: {exc}"


def record_experiment_run(experiment, repo_path: Path, metadata_dir: str, 
                         is_multiple_run: bool = False,
                         cache_dict: dict = None,
                         openpyxl_missing_warned: bool = False) -> Tuple[bool, Optional[str], bool]:
    """
    Append the latest run metadata to the experiment spreadsheet when possible.
    
    Args:
        experiment: The Experiment object
        repo_path: Path to the repository root
        metadata_dir: Directory path containing run metadata
        is_multiple_run: Whether this is part of a multiple run sequence
        cache_dict: Optional dictionary for caching pending entries
        openpyxl_missing_warned: Whether openpyxl warning was already shown
        
    Returns:
        Tuple of (success: bool, message: Optional[str], openpyxl_warned: bool)
    """
    import importlib
    import config
    from datetime import datetime, date
    
    db_path = getattr(config, "experiment_database_path", "")
    if not db_path:
        return (True, None, openpyxl_missing_warned)
    
    try:
        openpyxl_module = importlib.import_module("openpyxl")
    except ImportError:
        if not openpyxl_missing_warned:
            return (False, "openpyxl not installed - experiment log will not be updated.", True)
        return (False, None, True)

    Workbook = getattr(openpyxl_module, "Workbook", None)
    load_workbook = getattr(openpyxl_module, "load_workbook", None)
    if Workbook is None or load_workbook is None:
        if not openpyxl_missing_warned:
            return (False, "openpyxl is missing workbook support - experiment log updates disabled.", True)
        return (False, None, True)

    try:
        data_validation_module = importlib.import_module("openpyxl.worksheet.datavalidation")
        DataValidation = getattr(data_validation_module, "DataValidation", None)
    except ImportError:
        DataValidation = None

    try:
        utils_module = importlib.import_module("openpyxl.utils")
        get_column_letter = getattr(utils_module, "get_column_letter", None)
    except ImportError:
        get_column_letter = None

    try:
        styles_module = importlib.import_module("openpyxl.styles")
        PatternFill = getattr(styles_module, "PatternFill", None)
        Font = getattr(styles_module, "Font", None)
        Alignment = getattr(styles_module, "Alignment", None)
        Border = getattr(styles_module, "Border", None)
        Side = getattr(styles_module, "Side", None)
    except ImportError:
        PatternFill = None
        Font = None
        Alignment = None
        Border = None
        Side = None
    if Border is None or Side is None:
        try:
            borders_module = importlib.import_module("openpyxl.styles.borders")
            Border = getattr(borders_module, "Border", Border)
            Side = getattr(borders_module, "Side", Side)
        except ImportError:
            Border = Border or None
            Side = Side or None

    desired_headers = [
        "Date\n(dd.mm.yyyy)",
        "Experiment",
        "Time",
        "Scanned variable",
        "Scan range",
        "Scan steps",
        "Number of runs",
        "Good data\n(Y/N)",
        "Data path",
        "Comment"
    ]
    default_column_width = 25
    row_height = 20
    header_row_height = 30
    header_aliases = {
        "Scanned variables": "Scanned variable",
        "Scan ranges": "Scan range",
        "Comments": "Comment",
        "Date (dd.mm.yyyy)": "Date\n(dd.mm.yyyy)",
        "Good data (Y/N)": "Good data\n(Y/N)"
    }

    metadata_path = Path(metadata_dir)
    db_file = Path(db_path)
    try:
        db_file.parent.mkdir(parents=True, exist_ok=True)
        if db_file.exists():
            workbook = load_workbook(db_file)
            sheet = workbook.active
        else:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Experiments"

    except Exception as exc:
        return (False, f"Could not update experiment log: {exc}", openpyxl_missing_warned)

    def restructure_sheet_if_needed():
        existing_headers = []
        if sheet.max_row >= 1:
            existing_headers = [cell.value if cell.value is not None else "" for cell in sheet[1]]
        if not any(existing_headers):
            if sheet.max_row:
                sheet.delete_rows(1, sheet.max_row)
            sheet.append(desired_headers)
            return
        if existing_headers == desired_headers:
            return
        rows_snapshot = []
        for row in sheet.iter_rows(min_row=2):
            info = {}
            for idx, cell in enumerate(row):
                header_key = existing_headers[idx] if idx < len(existing_headers) else f"__extra_{idx}"
                canonical_key = header_aliases.get(header_key, header_key)
                info[canonical_key] = (cell.value, cell.hyperlink.target if cell.hyperlink else None)
            rows_snapshot.append(info)
        sheet.delete_rows(1, sheet.max_row)
        sheet.append(desired_headers)

        def get_value(info, key, default=""):
            packed = info.get(key)
            if packed is None:
                return default
            value, _ = packed
            return value if value is not None else default

        def get_link(info, key):
            packed = info.get(key)
            if packed is None:
                return None
            _, link = packed
            return link

        for stored in rows_snapshot:
            row_values = [
                get_value(stored, "Date\n(dd.mm.yyyy)"),
                get_value(stored, "Experiment"),
                get_value(stored, "Time"),
                get_value(stored, "Scanned variable"),
                get_value(stored, "Scan range"),
                get_value(stored, "Scan steps"),
                get_value(stored, "Number of runs"),
                get_value(stored, "Good data\n(Y/N)"),
                "path",
                get_value(stored, "Comment")
            ]
            sheet.append(row_values)
            current_row = sheet.max_row
            date_cell_snapshot = sheet.cell(row=current_row, column=1)
            if isinstance(date_cell_snapshot.value, (datetime, date)):
                date_cell_snapshot.number_format = "dd.mm.yyyy"
            link_target = get_link(stored, "Data path")
            if not link_target:
                link_target = get_value(stored, "Data path")
            if link_target:
                data_cell = sheet.cell(row=current_row, column=9)
                data_cell.value = "path"
                data_cell.hyperlink = link_target
                data_cell.style = "Hyperlink"
            sheet.row_dimensions[current_row].height = row_height

    restructure_sheet_if_needed()

    header_fill = PatternFill(fill_type="solid", fgColor="D9D9D9") if PatternFill else None
    header_font = Font(bold=True) if Font else None
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True) if Alignment else None
    header_border_side = Side(style="thin", color="000000") if Side else None

    for idx, header in enumerate(desired_headers, start=1):
        cell = sheet.cell(row=1, column=idx, value=header)
        if header_font:
            cell.font = header_font
        if header_fill:
            cell.fill = header_fill
        if header_alignment:
            cell.alignment = header_alignment
        if Border and header_border_side:
            cell.border = Border(
                left=header_border_side,
                right=header_border_side,
                top=header_border_side,
                bottom=header_border_side
            )

    if get_column_letter is not None:
        width_map = {
            1: 14,  # Date
            3: 10,  # Time
            5: 20,  # Scan range
            6: 16,  # Scan points number
            7: 16,  # Number of runs
            8: 10,  # Good data
            9: 10,  # Data path
            10: 40  # Comment
        }
        for col_idx in range(1, len(desired_headers) + 1):
            column_letter = get_column_letter(col_idx)
            width = width_map.get(col_idx, default_column_width)
            sheet.column_dimensions[column_letter].width = width

    sheet.row_dimensions[1].height = header_row_height
    sheet.freeze_panes = "A2"

    timestamp_iso = getattr(experiment.experimental_data, "current_run_timestamp", "")
    try:
        run_ts = datetime.fromisoformat(timestamp_iso) if timestamp_iso else datetime.now()
    except ValueError:
        run_ts = datetime.now()

    experiment_name = getattr(experiment.experimental_data, "experiment_name", "") or ""
    date_value = run_ts.date()
    time_value = run_ts.time().replace(microsecond=0)

    scanned_variables = []
    scan_ranges = []
    for variable in getattr(experiment, "scanned_variables", []):
        name = getattr(variable, "name", "")
        if name and name != "None":
            scanned_variables.append(str(name))
            min_val = getattr(variable, "min_val", "")
            max_val = getattr(variable, "max_val", "")
            scan_ranges.append(f"{min_val} -> {max_val}")

    # compute total number of scan points as product of per-variable `num_scan_steps` (default 1)
    scan_points = 1
    if getattr(experiment, "do_scan", False) and getattr(experiment, "scanned_variables_count", 0) > 0:
        try:
            total = 1
            for variable in getattr(experiment, "scanned_variables", []):
                if getattr(variable, "name", "") != "None":
                    total *= int(getattr(variable, "num_scan_steps", 1))
            scan_points = max(1, int(total))
        except (TypeError, ValueError):
            scan_points = 1

    number_of_runs_value = getattr(experiment, "number_of_runs", 1)
    try:
        number_of_runs_value = int(number_of_runs_value)
    except (TypeError, ValueError):
        number_of_runs_value = 1
    if number_of_runs_value <= 0:
        number_of_runs_value = 1
    if not is_multiple_run:
        number_of_runs_value = 1

    pending_entries = load_pending_log_entries(repo_path, cache_dict)

    current_entry = {
        "date": date_value.isoformat(),
        "experiment": experiment_name,
        "time": time_value.strftime("%H:%M:%S"),
        "scanned_variables": scanned_variables,
        "scan_ranges": scan_ranges,
        "scan_points": int(scan_points),
        "number_of_runs": int(number_of_runs_value),
        "good_data": "",
        "metadata_path": str(metadata_path),
        "comment": ""
    }

    entries_to_write = list(pending_entries)
    entries_to_write.append(current_entry)

    def append_entry_to_sheet(entry_dict):
        date_field = entry_dict.get("date")
        if isinstance(date_field, date):
            date_obj = date_field
        elif isinstance(date_field, datetime):
            date_obj = date_field.date()
        elif isinstance(date_field, str):
            try:
                date_obj = date.fromisoformat(date_field)
            except ValueError:
                try:
                    date_obj = datetime.fromisoformat(date_field).date()
                except ValueError:
                    date_obj = datetime.now().date()
        else:
            date_obj = datetime.now().date()

        time_field = entry_dict.get("time")
        if isinstance(time_field, datetime):
            time_obj = time_field.time().replace(microsecond=0)
        elif isinstance(time_field, str):
            try:
                time_obj = datetime.strptime(time_field, "%H:%M:%S").time()
            except ValueError:
                try:
                    time_obj = datetime.fromisoformat(time_field).time()
                except ValueError:
                    time_obj = time_field
        else:
            time_obj = time_field if time_field else datetime.now().time().replace(microsecond=0)

        scanned_field = entry_dict.get("scanned_variables", [])
        if isinstance(scanned_field, (list, tuple)):
            scanned_str = "; ".join(str(item) for item in scanned_field if item not in (None, ""))
        else:
            scanned_str = str(scanned_field) if scanned_field is not None else ""

        range_field = entry_dict.get("scan_ranges", [])
        if isinstance(range_field, (list, tuple)):
            ranges_str = "; ".join(str(item) for item in range_field if item not in (None, ""))
        else:
            ranges_str = str(range_field) if range_field is not None else ""

        scan_points_field = entry_dict.get("scan_points", 1)
        try:
            scan_points_value = int(scan_points_field)
        except (TypeError, ValueError):
            scan_points_value = 1
        if scan_points_value <= 0:
            scan_points_value = 1

        number_of_runs_field = entry_dict.get("number_of_runs", 1)
        try:
            number_of_runs_int = int(number_of_runs_field)
        except (TypeError, ValueError):
            number_of_runs_int = 1
        if number_of_runs_int <= 0:
            number_of_runs_int = 1

        good_data_value = entry_dict.get("good_data", "") or ""
        comment_value = entry_dict.get("comment", "") or ""
        metadata_value = entry_dict.get("metadata_path", "")

        row_values_local = [
            date_obj,
            entry_dict.get("experiment", ""),
            time_obj,
            scanned_str,
            ranges_str,
            scan_points_value,
            number_of_runs_int,
            good_data_value,
            "path" if metadata_value else "",
            comment_value
        ]

        sheet.append(row_values_local)
        row_index = sheet.max_row
        date_cell_local = sheet.cell(row=row_index, column=1)
        if isinstance(date_cell_local.value, (datetime, date)):
            date_cell_local.number_format = "d.m.yyyy"
        if metadata_value:
            data_cell_local = sheet.cell(row=row_index, column=9)
            data_cell_local.value = "path"
            data_cell_local.hyperlink = metadata_value
            data_cell_local.style = "Hyperlink"
        sheet.row_dimensions[row_index].height = row_height

    for entry_dict in entries_to_write:
        append_entry_to_sheet(entry_dict)

    if DataValidation is not None:
        target_range = "H2:H1048576"
        existing_range = False
        if hasattr(sheet, "data_validations"):
            for dv in sheet.data_validations.dataValidation:
                if any(str(rng) == target_range for rng in dv.ranges):
                    existing_range = True
                    break
        if not existing_range:
            dv = DataValidation(type="list", formula1='"[ ],[x]"', allow_blank=True)
            dv.error = "Select [x] once the dataset is validated."
            dv.prompt = "Switch to [x] when the run produced good data."
            sheet.add_data_validation(dv)
            dv.add(target_range)

    for row_idx in range(2, sheet.max_row + 1):
        sheet.row_dimensions[row_idx].height = row_height

    try:
        workbook.save(db_file)
    except PermissionError:
        set_pending_log_entries(repo_path, entries_to_write, cache_dict)
        return (False, "Experiment log update deferred: close the Excel workbook to allow writing. Pending entries will be retried automatically.", openpyxl_missing_warned)
    except Exception as exc:
        set_pending_log_entries(repo_path, entries_to_write, cache_dict)
        return (False, f"Could not update experiment log (will retry later): {exc}", openpyxl_missing_warned)

    message = None
    if pending_entries:
        message = "Previously pending experiment log entries were written to the log file."
    set_pending_log_entries(repo_path, [], cache_dict)
    return (True, message, openpyxl_missing_warned)


def remove_experiment_log_rows(experiment_name: str, repo_path: Path = None) -> Tuple[bool, Optional[str]]:
    """
    Remove rows in the experiment log workbook that match the given experiment name.
    
    Args:
        experiment_name: Name of the experiment to remove
        repo_path: Optional path to repository root (only used for logging context)
        
    Returns:
        Tuple of (success: bool, message: Optional[str])
    """
    import importlib
    import config
    
    db_path = getattr(config, "experiment_database_path", "")
    if not db_path or not experiment_name:
        return (True, None)

    try:
        openpyxl_module = importlib.import_module("openpyxl")
    except ImportError:
        return (False, "openpyxl not installed - experiment log cleanup skipped.")

    load_workbook = getattr(openpyxl_module, "load_workbook", None)
    if load_workbook is None:
        return (False, "openpyxl missing load_workbook - experiment log cleanup skipped.")

    try:
        workbook = load_workbook(db_path)
    except FileNotFoundError:
        return (True, None)
    except PermissionError:
        return (False, "Experiment log cleanup skipped: close the Excel workbook and retry.")
    except Exception as exc:
        return (False, f"Could not load experiment log for cleanup: {exc}")

    try:
        sheet = workbook.active
        if sheet.max_row <= 1:
            return (True, None)

        rows_to_delete = []
        for row_idx in range(2, sheet.max_row + 1):
            cell_value = sheet.cell(row=row_idx, column=2).value
            match = False
            if isinstance(cell_value, str):
                match = cell_value.strip() == experiment_name
            elif cell_value is not None:
                try:
                    match = str(cell_value).strip() == experiment_name
                except Exception:
                    match = False
            if match:
                rows_to_delete.append(row_idx)

        if not rows_to_delete:
            return (True, None)

        for row_idx in reversed(rows_to_delete):
            sheet.delete_rows(row_idx)

        try:
            workbook.save(db_path)
        except PermissionError:
            return (False, "Experiment log cleanup could not save: close the Excel workbook and retry.")
        except Exception as exc:
            return (False, f"Could not save experiment log after cleanup: {exc}")
    finally:
        try:
            workbook.close()
        except Exception:
            pass
    
    return (True, None)
