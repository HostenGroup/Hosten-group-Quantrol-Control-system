from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import numpy as np
from astropy.modeling import fitting, models
from tqdm import tqdm

try:
    from tifffile import imread as read_tiff  # type: ignore[import-not-found]
except ImportError:
    import matplotlib.pyplot as plt

    read_tiff = plt.imread


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
TAKE_LAST_N = 1

FIRST_VARIABLE_FASTEST = True
OUTPUT_BASENAME = "field_sweep_results"

WIDTH_PX_REF = 2048
HEIGHT_PX_REF = 1536

ATOM_COUNT_FILE = Path(__file__).resolve().parent.parent / "atom_count.py"

_reported_tiff_fallback = False


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


def read_tiff_fallback_safe(path: str) -> np.ndarray:
    global _reported_tiff_fallback
    try:
        return np.asarray(read_tiff(path), dtype=np.float32)
    except Exception as exc:
        import matplotlib.pyplot as plt

        if not _reported_tiff_fallback:
            print(f"TIFF fast loader unavailable for some files ({exc}); using matplotlib fallback")
            _reported_tiff_fallback = True
        return np.asarray(plt.imread(path), dtype=np.float32)


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


def parse_scan_axis(scan_entry: dict) -> np.ndarray:
    if "num_scan_steps" not in scan_entry:
        raise ValueError(f"Missing num_scan_steps in scanned variable: {scan_entry}")

    n_steps = int(scan_entry["num_scan_steps"])
    if n_steps <= 0:
        raise ValueError(f"Invalid num_scan_steps: {n_steps}")

    vmin = float(scan_entry["min_val"])
    vmax = float(scan_entry["max_val"])
    return np.linspace(vmin, vmax, n_steps)


def parse_settings(metadata: dict) -> tuple[dict, list[dict], list[np.ndarray]]:
    camera = metadata["experimental_data"]["camera"]
    scanned_variables = metadata.get("scanned_variables", [])

    if len(scanned_variables) != 3:
        raise ValueError(
            f"Expected exactly 3 scanned variables, got {len(scanned_variables)}"
        )

    axes = [parse_scan_axis(scan) for scan in scanned_variables]
    settings = {
        "gain_db": float(camera["gain_db"]),
        "exposure_time_s": float(camera["exposure_time_ms"]) * 1e-3,
        "pixel_format": camera["format_name"],
    }
    return settings, scanned_variables, axes


def fit_1d_gaussian(profile: np.ndarray) -> float:
    profile = np.asarray(profile, dtype=float)
    x = np.arange(profile.size, dtype=float)

    if profile.size < 5 or not np.any(np.isfinite(profile)):
        return float("nan")

    y = np.where(np.isfinite(profile), profile, 0.0)
    y_min = float(np.min(y))
    y_max = float(np.max(y))
    amp_guess = max(y_max - y_min, 1.0)
    mean_guess = float(np.argmax(y))
    std_guess = max(profile.size / 8.0, 1.0)

    fitter = fitting.TRFLSQFitter()
    model = models.Gaussian1D(
        amplitude=amp_guess,
        mean=mean_guess,
        stddev=std_guess,
    ) + models.Const1D(amplitude=y_min)

    model.amplitude_0.bounds = (0.0, None)
    model.stddev_0.bounds = (0.5, float(profile.size))

    try:
        fit_model = fitter(model, x, y, filter_non_finite=True)
        return float(abs(fit_model.stddev_0.value))
    except Exception:
        return float("nan")


def pixel_sigma_to_meters(sigma_x_px: float, sigma_y_px: float) -> tuple[float, float]:
    sigma_x_m = abs(float(sigma_x_px)) / WIDTH_PX_REF * 8e-3
    sigma_y_m = abs(float(sigma_y_px)) / HEIGHT_PX_REF * 6e-3
    return sigma_x_m, sigma_y_m


def compute_anisotropy(sigma_x_m: float, sigma_y_m: float) -> float:
    denom = sigma_x_m + sigma_y_m
    if not np.isfinite(denom) or denom <= 0.0:
        return float("nan")
    return float(abs((sigma_x_m - sigma_y_m) / denom))


def average_over_repetitions(values: np.ndarray, n_grid: int) -> tuple[np.ndarray, int]:
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.size < n_grid:
        raise ValueError(
            f"Not enough points for grid: got {arr.size}, need at least {n_grid}"
        )

    usable = (arr.size // n_grid) * n_grid
    if usable != arr.size:
        print(
            f"Warning: {arr.size - usable} trailing points ignored to fit integer repetitions"
        )
        arr = arr[:usable]

    reps = arr.size // n_grid
    grouped = arr.reshape(reps, n_grid)
    return np.nanmean(grouped, axis=0), reps


def reshape_flat_to_grid(flat: np.ndarray, axis_lengths: list[int]) -> np.ndarray:
    shape = tuple(axis_lengths)
    order = "F" if FIRST_VARIABLE_FASTEST else "C"
    return np.asarray(flat, dtype=float).reshape(shape, order=order)


def save_processed_data(
    directory: Path,
    scanned_variables: list[dict],
    scan_axes: list[np.ndarray],
    atom_grid: np.ndarray,
    anis_grid: np.ndarray,
    repetitions: int,
    pair_count: int,
) -> None:
    output_npz = directory / f"{OUTPUT_BASENAME}.npz"
    output_json = directory / f"{OUTPUT_BASENAME}_meta.json"

    np.savez(
        output_npz,
        atom_grid=atom_grid,
        anisotropy_grid=anis_grid,
        axis_0=np.asarray(scan_axes[0], dtype=float),
        axis_1=np.asarray(scan_axes[1], dtype=float),
        axis_2=np.asarray(scan_axes[2], dtype=float),
    )

    metadata_payload = {
        "variable_names": [str(scan["name"]) for scan in scanned_variables],
        "axis_lengths": [int(len(a)) for a in scan_axes],
        "first_variable_fastest": bool(FIRST_VARIABLE_FASTEST),
        "averaged_repetitions": int(repetitions),
        "image_pairs_processed": int(pair_count),
        "npz_file": output_npz.name,
    }
    output_json.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")
    print(f"Saved processed data: {output_npz}")
    print(f"Saved metadata: {output_json}")


def process_directory(directory: Path) -> None:
    directory = Path(directory)
    metadata_file = find_metadata_file(directory)

    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    settings, scanned_variables, scan_axes = parse_settings(metadata)
    axis_lengths = [len(axis) for axis in scan_axes]
    n_grid = int(np.prod(axis_lengths))

    sorted_tifs = sort_tif_files(directory)
    image_pairs = make_background_image_pairs(sorted_tifs)

    atom_numbers: list[float] = []
    anisotropy_values: list[float] = []

    for bg_path, img_path in tqdm(image_pairs, desc="Processing field sweep pairs"):
        image = read_tiff_fallback_safe(str(img_path))
        background = read_tiff_fallback_safe(str(bg_path))
        subtracted = np.asarray(image - background, dtype=np.float32)

        counts = float(np.sum(subtracted))
        atom_number = float(
            atom_count(
                counts,
                settings["gain_db"],
                settings["exposure_time_s"],
                settings["pixel_format"],
            )
        )

        profile_x = np.sum(subtracted, axis=0)
        profile_y = np.sum(subtracted, axis=1)
        sigma_x_px = fit_1d_gaussian(profile_x)
        sigma_y_px = fit_1d_gaussian(profile_y)

        sigma_x_m, sigma_y_m = pixel_sigma_to_meters(sigma_x_px, sigma_y_px)
        anisotropy = compute_anisotropy(sigma_x_m, sigma_y_m)

        atom_numbers.append(atom_number)
        anisotropy_values.append(anisotropy)

    atom_flat_mean, reps = average_over_repetitions(np.asarray(atom_numbers), n_grid)
    anis_flat_mean, _ = average_over_repetitions(np.asarray(anisotropy_values), n_grid)

    atom_grid = reshape_flat_to_grid(atom_flat_mean, axis_lengths)
    anis_grid = reshape_flat_to_grid(anis_flat_mean, axis_lengths)

    print(f"Mapped to grid shape {atom_grid.shape}; averaged repetitions per point: {reps}")
    save_processed_data(
        directory=directory,
        scanned_variables=scanned_variables,
        scan_axes=scan_axes,
        atom_grid=atom_grid,
        anis_grid=anis_grid,
        repetitions=reps,
        pair_count=len(image_pairs),
    )


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=TAKE_LAST_N)

    for directory in target_directories:
        process_directory(directory)


if __name__ == "__main__":
    main()
