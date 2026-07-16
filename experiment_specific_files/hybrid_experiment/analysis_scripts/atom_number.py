from __future__ import annotations

import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
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
MAX_IMAGE_PAIR_WORKERS = 8
CAMERA_COUNTS_FILENAME = "camera_counts.txt"

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


def compute_camera_count(pair: tuple[Path, Path]) -> float:
    """Load one background/image pair and return the summed camera counts."""
    background_path, image_path = pair
    image = read_tiff_fallback_safe(str(image_path))
    background = read_tiff_fallback_safe(str(background_path))
    return float(np.sum(image - background))


def compute_camera_count_indexed(index: int, pair: tuple[Path, Path]) -> tuple[int, float]:
    """Load one pair and return its index with the summed camera counts."""
    return index, compute_camera_count(pair)


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        process_directory(directory)


def get_scanned_variables(metadata: dict) -> list[dict]:
    """Return scanned variables sorted by Dim."""
    scanned_variables = metadata.get("scanned_variables", [])
    if not scanned_variables:
        return []

    return sorted(scanned_variables, key=lambda item: int(item["Dim"]))


def build_atom_number_header(
    data_shape: tuple[int, ...],
    scan_shape: tuple[int, ...],
    number_of_runs: int,
    scanned_variables: list[dict],
) -> str:
    """Build a short self-describing header for the flattened tensor output."""
    dim_order = ", ".join(str(int(variable["Dim"])) for variable in scanned_variables)
    scan_names = ", ".join(str(variable["name"]) for variable in scanned_variables)
    scan_shape_text = ", ".join(str(int(size)) for size in scan_shape)
    shape_text = ", ".join(str(int(size)) for size in data_shape)
    return "\n".join(
        [
            f"data_shape: {shape_text}",
            f"scan_shape: {scan_shape_text}",
            f"run_count: {int(number_of_runs)}",
            f"scan_dim_order: {dim_order}",
            f"scan_names: {scan_names}",
            "flattening_order: C",
        ]
    )


def print_atom_number_summary(atom_numbers: np.ndarray, number_of_runs: int) -> None:
    """Print a compact atom-number summary for console-only use."""
    values = np.asarray(atom_numbers, dtype=float).reshape(-1)
    if values.size == 0:
        raise ValueError("No atom numbers available to summarize")

    if int(number_of_runs) > 1 or values.size > 1:
        mean_value = float(np.mean(values))
        std_value = float(np.std(values))
        print(f"Atom number mean: {mean_value*1e-6:.3f}  million ({values.size} runs)")
        print(f"Atom number standard deviation: {std_value*1e-6:.3f} million")
        print(f"Atom number standard error of the mean: {std_value*1e-6/np.sqrt(values.size):.3f} million")
    else:
        print(f"Atom number: {float(values[0])*1e-6:.3f} million")

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
    return {
        "gain_db": float(camera["gain_db"]),
        "exposure_time_s": float(camera["exposure_time_ms"]) * 1e-3,
        "pixel_format": camera["format_name"],
    }


def parse_number_of_runs(metadata: dict) -> int:
    """Read Quantrol's multiple-runs count from metadata."""
    try:
        is_multiple_runs = metadata.get("multiple_runs", 1)
        if is_multiple_runs:
            number_of_runs = int(metadata.get("number_of_runs", 1))
        else:
            number_of_runs = 1
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


def load_camera_counts_sidecar(path: Path) -> np.ndarray:
    """Load acquisition-time camera counts saved alongside the images."""
    if not path.exists():
        raise FileNotFoundError(f"Missing camera counts file: {path}")

    data = np.loadtxt(path, comments="#", ndmin=2)
    data = np.atleast_2d(np.asarray(data, dtype=float))
    if data.shape[1] < 2:
        raise ValueError(f"camera counts file {path} must contain at least two columns")

    image_indices = data[:, 0].astype(int)
    counts = data[:, 1].astype(float)
    order = np.argsort(image_indices)
    if not np.array_equal(image_indices[order], np.arange(image_indices.size)):
        raise ValueError(f"camera counts file {path} does not contain a contiguous 0-based index sequence")

    return counts[order]


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
    do_scan = bool(metadata.get("do_scan", False))
    scanned_variables = get_scanned_variables(metadata)
    print(f"Processing {directory}")
    print(f"Using metadata file: {metadata_file.name}")

    counts_path = directory / CAMERA_COUNTS_FILENAME
    counts: np.ndarray | None = None
    if counts_path.exists():
        try:
            counts = load_camera_counts_sidecar(counts_path)
            print(f"Using acquisition-time camera counts: {counts_path.name}")
        except Exception as exc:
            print(f"Warning: could not load {counts_path.name} ({exc}); falling back to TIFF processing")

    if counts is None:
        sorted_tifs = sort_tif_files(directory)
        image_pairs = make_background_image_pairs(sorted_tifs)
        max_workers = min(MAX_IMAGE_PAIR_WORKERS, len(image_pairs)) or 1
        counts_list = [0.0] * len(image_pairs)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(compute_camera_count_indexed, index, pair) for index, pair in enumerate(image_pairs)]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing image pairs"):
                index, count = future.result()
                counts_list[index] = count
        counts = np.asarray(counts_list, dtype=float)

    if counts.size % 2 != 0:
        print(f"Warning: {counts.size} image counts found; ignoring the last count to form background/image pairs")

    usable_image_count = (counts.size // 2) * 2
    if usable_image_count <= 0:
        raise ValueError("Not enough image counts to build a scan grid")

    pair_counts = counts[:usable_image_count].reshape((-1, 2))
    differential_counts = pair_counts[:, 1] - pair_counts[:, 0]
    atom_numbers = np.asarray(
        atom_count(
            np.asarray(differential_counts, dtype=float),
            settings["gain_db"],
            settings["exposure_time_s"],
            settings["pixel_format"],
        ),
        dtype=float,
    )

    if not do_scan:
        print_atom_number_summary(atom_numbers, number_of_runs)
        return

    scan_shape = tuple(int(variable["num_scan_steps"]) for variable in scanned_variables)

    if not scan_shape:
        raise ValueError("No scan dimensions found in metadata")

    points_per_run = int(np.prod(scan_shape))
    if points_per_run <= 0:
        raise ValueError("Scan grid has no points")

    usable_pair_count = (differential_counts.size // points_per_run) * points_per_run
    if usable_pair_count <= 0:
        raise ValueError("Not enough image pairs to build a scan grid")
    if usable_pair_count != differential_counts.size:
        print(
            f"Warning: {differential_counts.size} image pairs is not divisible by the scan grid size {points_per_run}; "
            f"ignoring the last {differential_counts.size - usable_pair_count} pair(s)"
        )

    actual_runs = usable_pair_count // points_per_run
    if actual_runs <= 0:
        raise ValueError("Could not infer any complete scan runs from the image pairs")
    if actual_runs != number_of_runs:
        print(
            f"Warning: metadata says {number_of_runs} run(s) but the image stack contains {actual_runs} complete run(s)"
        )

    atom_numbers = atom_numbers[:usable_pair_count].reshape((actual_runs, *scan_shape))
    header = build_atom_number_header(atom_numbers.shape, scan_shape, actual_runs, scanned_variables)
    np.savetxt(directory / "atom_numbers.txt", atom_numbers.reshape(-1), header=header)

    print(f"Saved: {directory / 'atom_numbers.txt'}")


if __name__ == "__main__":
    main()