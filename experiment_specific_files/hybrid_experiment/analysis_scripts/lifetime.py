from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.modeling import fitting
from astropy.modeling.models import custom_model
from tqdm import tqdm

try:
    from tifffile import imread as read_tiff  # type: ignore[import-not-found]
except ImportError:
    read_tiff = plt.imread


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
FORCE_ZERO_OFFSET = False
SKIP_FIRST_POINTS_NUMBER = 0

ATOM_COUNT_FILE = (
    Path(__file__).resolve().parent.parent
    / "atom_count.py"
)


def load_atom_count_function():
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
    global _reported_tiff_fallback
    try:
        return np.asarray(read_tiff(path), dtype=np.float32)
    except Exception as exc:
        if not _reported_tiff_fallback:
            print(f"TIFF fast loader unavailable for some files ({exc}); using matplotlib fallback")
            _reported_tiff_fallback = True
        return np.asarray(plt.imread(path), dtype=np.float32)


@custom_model
def lifetime_model(t, n0=1.0e6, tau=0.1, offset=0.0):
    """Exponential decay model: N(t) = N0 * exp(-t/tau) + offset."""
    return n0 * np.exp(-t / tau) + offset


def load_target_directories(path_list_file: Path, take_last_n: int = 1) -> list[Path]:
    if not path_list_file.exists():
        raise FileNotFoundError(f"Path list file not found: {path_list_file}")

    with path_list_file.open("r", encoding="utf-8") as file:
        raw_dirs = [line.strip() for line in file if line.strip()]

    if not raw_dirs:
        raise ValueError(f"No directories found in {path_list_file}")

    return [Path(line) for line in raw_dirs][-take_last_n:]


def find_metadata_file(images_directory: Path) -> Path:
    candidates = list(images_directory.parent.glob("metadata*.json"))
    if not candidates:
        raise FileNotFoundError(f"No metadata*.json found in {images_directory.parent}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_settings(metadata: dict) -> dict:
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


def sort_tif_files(directory: Path) -> list[Path]:
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
    if len(sorted_tifs) < 2:
        raise ValueError("Need at least 2 tif files (background + image)")

    if len(sorted_tifs) % 2 != 0:
        print("Warning: odd number of tif files; last file will be ignored")
        sorted_tifs = sorted_tifs[:-1]

    return [(sorted_tifs[i], sorted_tifs[i + 1]) for i in range(0, len(sorted_tifs), 2)]


def compute_atom_numbers_from_images(directory: Path, settings: dict) -> np.ndarray:
    sorted_tifs = sort_tif_files(directory)
    image_pairs = make_background_image_pairs(sorted_tifs)

    counts: list[float] = []
    for background_path, image_path in tqdm(image_pairs, desc="Processing lifetime pairs"):
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


def compute_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_t = y_true[valid]
    y_p = y_pred[valid]
    if y_t.size < 2:
        return float("nan")

    ss_res = float(np.sum((y_t - y_p) ** 2))
    ss_tot = float(np.sum((y_t - np.mean(y_t)) ** 2))
    if ss_tot <= 0.0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def build_output_timestamp(directory: Path) -> str:
    """Build a TOF-style timestamp from the directory name when possible."""
    try:
        date_str = directory.parent.parent.name
        time_str = directory.parent.name
        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y_%m_%d_%H_%M_%S")
        return dt.strftime("%Y%m%d_%H%M%S")
    except Exception:
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_experiment_root(directory: Path) -> Path:
    """Return the experiment root above date/time/image folders."""
    return directory.parents[2]


def process_directory(directory: Path) -> None:
    directory = Path(directory)
    metadata_file = find_metadata_file(directory)

    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    settings = parse_settings(metadata)
    atom_numbers = compute_atom_numbers_from_images(directory, settings)

    scanned = metadata.get("scanned_variables", [])
    if not scanned:
        raise ValueError("metadata['scanned_variables'] is empty")

    scan_min_ms = settings["scan_min_ms"]
    scan_max_ms = settings["scan_max_ms"]
    scan_label = metadata.get("experimental_data", {}).get("comment", "Time (ms)")

    time_ms = np.linspace(scan_min_ms, scan_max_ms, atom_numbers.shape[0])
    time_s = time_ms * 1e-3

    valid = np.isfinite(time_s) & np.isfinite(atom_numbers) & (atom_numbers >= 0)
    t_fit = time_s[valid]
    n_fit = atom_numbers[valid]

    if not isinstance(SKIP_FIRST_POINTS_NUMBER, int):
        raise TypeError("SKIP_FIRST_POINTS_NUMBER must be an int")
    if SKIP_FIRST_POINTS_NUMBER < 0:
        raise ValueError("SKIP_FIRST_POINTS_NUMBER must be >= 0")

    if SKIP_FIRST_POINTS_NUMBER > 0:
        t_fit = t_fit[SKIP_FIRST_POINTS_NUMBER:]
        n_fit = n_fit[SKIP_FIRST_POINTS_NUMBER:]

    if t_fit.size < 3:
        raise ValueError("Not enough valid data points for exponential lifetime fit")

    n0_guess = float(max(np.max(n_fit) - np.min(n_fit), 1.0))
    tau_guess = float(max((np.max(t_fit) - np.min(t_fit)) / 2.0, 1e-6))
    offset_guess = 0.0 if FORCE_ZERO_OFFSET else float(np.min(n_fit))

    fit = fitting.TRFLSQFitter()
    model_init = lifetime_model(n0=n0_guess, tau=tau_guess, offset=offset_guess)
    model_init.n0.bounds = (0.0, None)
    model_init.tau.bounds = (1e-9, None)
    if FORCE_ZERO_OFFSET:
        model_init.offset.fixed = True
        model_init.offset.value = 0.0

    model_fit = fit(model_init, t_fit, n_fit, filter_non_finite=True)

    n_pred = np.asarray(model_fit(t_fit), dtype=float)
    r2 = compute_r2(n_fit, n_pred)

    fig, ax = plt.subplots(figsize=(12, 7), dpi=120)
    ax.plot(t_fit * 1e3, n_fit * 1e-6, "o", ms=4, label="Data")

    t_dense_ms = np.linspace(np.min(t_fit * 1e3), np.max(t_fit * 1e3), 300)
    t_dense_s = t_dense_ms * 1e-3
    n_dense = np.asarray(model_fit(t_dense_s), dtype=float)

    if np.isfinite(r2):
        fit_label = f"Exp fit (tau={model_fit.tau.value:.2e} s, R^2={r2:.4f})"
    else:
        fit_label = f"Exp fit (tau={model_fit.tau.value:.2e} s)"

    ax.plot(t_dense_ms, n_dense * 1e-6, "-", lw=2, label=fit_label)

    ax.set_title(str(directory))
    ax.set_xlabel(scan_label)
    ax.set_ylabel("Atom number (million)")
    ax.grid(True, which="both", alpha=0.35)
    ax.minorticks_on()
    ax.legend()
    fig.tight_layout()

    data_timestamp = build_output_timestamp(directory)
    output_path = get_experiment_root(directory) / f"lifetime_{data_timestamp}.png"
    fig.savefig(output_path, dpi=150)
    print(f"Saved figure: {output_path}")

    plt.show()


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        process_directory(directory)


if __name__ == "__main__":
    main()
