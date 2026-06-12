from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

try:
    from tifffile import imread as read_tiff  # type: ignore[import-not-found]
except ImportError:
    read_tiff = plt.imread


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"

ATOM_COUNT_FILE = Path(__file__).resolve().parents[1] / "atom_count.py"


def load_atom_count_function():
    """Load atom_count() from the shared hybrid_experiment source file."""
    if not ATOM_COUNT_FILE.exists():
        raise FileNotFoundError(f"atom_count source not found: {ATOM_COUNT_FILE}")

    spec = importlib.util.spec_from_file_location("hybrid_atom_count", ATOM_COUNT_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from {ATOM_COUNT_FILE}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.atom_count


atom_count = load_atom_count_function()

_reported_tiff_fallback = False


def read_tiff_fallback_safe(path: str) -> np.ndarray:
    """Read TIFF with tifffile when possible, fallback to matplotlib on decode issues."""
    global _reported_tiff_fallback
    try:
        return np.asarray(read_tiff(path), dtype=np.float32)
    except Exception as exc:
        if not _reported_tiff_fallback:
            print(f"TIFF fast loader unavailable for some files ({exc}); using matplotlib fallback")
            _reported_tiff_fallback = True
        return np.asarray(plt.imread(path), dtype=np.float32)


def load_target_directories(path_list_file: Path, take_last_n: int = 1) -> list[Path]:
    """Load target image directories from a path list file."""
    if not path_list_file.exists():
        raise FileNotFoundError(f"Path list file not found: {path_list_file}")

    with path_list_file.open("r", encoding="utf-8") as file:
        raw_dirs = [line.strip() for line in file if line.strip()]

    if not raw_dirs:
        raise ValueError(f"No directories found in {path_list_file}")

    directories = [Path(line) for line in raw_dirs]
    return directories[-take_last_n:]


def find_metadata_file(images_directory: Path) -> Path:
    """Pick the newest metadata*.json from the parent directory."""
    candidates = list(images_directory.parent.glob("metadata*.json"))
    if not candidates:
        raise FileNotFoundError(f"No metadata*.json found in {images_directory.parent}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_settings(metadata: dict) -> dict:
    """Extract camera and scan settings used for atom-number conversion."""
    camera = metadata["experimental_data"]["camera"]
    scanned_variables = metadata["scanned_variables"]
    if not scanned_variables:
        raise ValueError("metadata['scanned_variables'] is empty")

    scan = scanned_variables[0]
    return {
        "gain_db": float(camera["gain_db"]),
        "exposure_time_s": float(camera["exposure_time_ms"]) * 1e-3,
        "pixel_format": camera["format_name"],
        "scan_min_ms": float(scan["min_val"]),
        "scan_max_ms": float(scan["max_val"]),
    }


def parse_number_of_runs(metadata: dict) -> int:
    """Read Quantrol's multiple-runs count from metadata."""
    try:
        number_of_runs = int(metadata.get("number_of_runs", 1))
    except (TypeError, ValueError):
        number_of_runs = 1
    return max(number_of_runs, 1)


def sort_tif_files(directory: Path) -> list[Path]:
    """Return .tif files sorted by numeric suffix if present."""
    tif_files = [p for p in directory.iterdir() if p.suffix.lower() == ".tif"]
    if not tif_files:
        raise ValueError(f"No .tif files found in {directory}")

    def sort_key(path: Path) -> tuple[int, str]:
        match = re.search(r"_(\d+)$", path.stem)
        if match:
            return int(match.group(1)), path.name
        any_number = re.search(r"(\d+)", path.stem)
        if any_number:
            return int(any_number.group(1)), path.name
        return 10**9, path.name

    return sorted(tif_files, key=sort_key)


def make_background_image_pairs(sorted_tifs: list[Path]) -> list[tuple[Path, Path]]:
    """Pair files as (background, image) using adjacent files."""
    if len(sorted_tifs) < 2:
        raise ValueError("Need at least 2 tif files (background + image)")

    if len(sorted_tifs) % 2 != 0:
        print("Warning: odd number of tif files; last file will be ignored")
        sorted_tifs = sorted_tifs[:-1]

    return [(sorted_tifs[i], sorted_tifs[i + 1]) for i in range(0, len(sorted_tifs), 2)]


def compute_atom_numbers_from_images(directory: Path, settings: dict) -> np.ndarray:
    """Compute atom numbers for each background/image pair in a directory."""
    sorted_tifs = sort_tif_files(directory)
    image_pairs = make_background_image_pairs(sorted_tifs)

    counts: list[float] = []
    for background_path, image_path in tqdm(image_pairs, desc="Processing image pairs"):
        image = read_tiff_fallback_safe(str(image_path))
        background = read_tiff_fallback_safe(str(background_path))
        counts.append(float(np.sum(image - background)))

    return np.asarray(
        np.vectorize(atom_count)(
            np.asarray(counts, dtype=float),
            settings["gain_db"],
            settings["exposure_time_s"],
            settings["pixel_format"],
        ),
        dtype=float,
    )


def save_atom_numbers(directory: Path, atom_numbers: np.ndarray, scan_values_ms: np.ndarray) -> None:
    """Save scan values and atom numbers next to the images."""
    table = np.column_stack((atom_numbers, scan_values_ms))
    np.savetxt(directory / "atom_numbers.txt", table, header="atom_number scan_value")


def process_directory(directory: Path) -> None:
    """Compute atom numbers for one image directory and save them to disk."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Image directory not found: {directory}")

    metadata_file = find_metadata_file(directory)
    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    settings = parse_settings(metadata)
    number_of_runs = parse_number_of_runs(metadata)
    print(f"Processing {directory}")
    print(f"Using metadata file: {metadata_file.name}")

    sorted_tifs = sort_tif_files(directory)
    image_pairs = make_background_image_pairs(sorted_tifs)
    atom_numbers = compute_atom_numbers_from_images(directory, settings)

    usable_pair_count = (len(image_pairs) // number_of_runs) * number_of_runs
    if usable_pair_count <= 0:
        raise ValueError("Not enough image pairs to build a multiple-runs scan")
    if usable_pair_count != len(image_pairs):
        print(
            f"Warning: {len(image_pairs)} image pairs is not divisible by {number_of_runs}; "
            f"ignoring the last {len(image_pairs) - usable_pair_count} pair(s)"
        )

    scan_points = usable_pair_count // number_of_runs
    if scan_points <= 0:
        raise ValueError("Multiple-runs scan would contain zero scan points")

    atom_numbers = atom_numbers[:usable_pair_count]
    scan_values_one_run = np.linspace(settings["scan_min_ms"], settings["scan_max_ms"], scan_points)
    scan_values_ms = np.tile(scan_values_one_run, number_of_runs)

    save_atom_numbers(directory, atom_numbers, scan_values_ms)

    print(f"Saved: {directory / 'atom_numbers.txt'}")


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        process_directory(directory)


if __name__ == "__main__":
    main()