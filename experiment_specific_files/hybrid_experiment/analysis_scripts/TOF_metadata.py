from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.modeling import fitting, models
from astropy.modeling.models import custom_model
from tqdm import tqdm

try:
    from tifffile import imread as read_tiff  # type: ignore[import-not-found]
except ImportError:
    # Fallback keeps script runnable in environments without tifffile.
    read_tiff = plt.imread


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

# All values are in SI units unless otherwise noted.
DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
FIT_DOWNSAMPLING_FACTOR = 4
ATOM_NUMBERS_SCRIPT = Path(__file__).resolve().with_name("atom_number.py")

PIXELS_PER_MM_BY_CAMERA = {
    "X": 330.0,
    "Y": 330.0,
    # "Y": 63.2,
    "Z": 63.2,
}


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        process_directory(directory)


@custom_model
def expansion_model(t, sigma0=0.001, T=100e-6):
    """Cloud width after time-of-flight expansion."""
    return np.sqrt(sigma0**2 + 94.868 * T * t**2)


@custom_model
def vertical_position_model(t, y0=0.0, a=9.81):
    """Constrained vertical motion model with zero linear term: y(t)=y0+0.5*a*t^2."""
    return y0 + 0.5 * a * t**2


def compute_weighted_fit_quality(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_err: np.ndarray,
    n_params: int,
) -> tuple[float, float]:
    """Return weighted-R2 and reduced-chi2 using uncertainty-aware residuals."""
    valid = np.isfinite(y_true) & np.isfinite(y_pred) & np.isfinite(y_err) & (y_err > 0)
    y_t = y_true[valid]
    y_p = y_pred[valid]
    s = y_err[valid]
    if y_t.size < max(n_params + 1, 2):
        return np.nan, np.nan

    w = 1.0 / (s**2)
    w_sum = float(np.sum(w))
    if w_sum <= 0.0:
        return np.nan, np.nan

    y_wmean = float(np.sum(w * y_t) / w_sum)
    ss_res_w = float(np.sum(w * (y_t - y_p) ** 2))
    ss_tot_w = float(np.sum(w * (y_t - y_wmean) ** 2))
    weighted_r2 = 1.0 - ss_res_w / ss_tot_w if ss_tot_w > 0 else np.nan

    dof = max(int(y_t.size) - int(n_params), 1)
    chi2_red = float(np.sum(((y_t - y_p) / s) ** 2) / dof)
    return weighted_r2, chi2_red


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


def run_atom_number_subprocess(directory: Path) -> np.ndarray:
    """Run atom_number.py for this directory and return the generated atom numbers."""
    if not ATOM_NUMBERS_SCRIPT.exists():
        raise FileNotFoundError(f"atom_number script not found: {ATOM_NUMBERS_SCRIPT}")

    command_code = (
        "import importlib.util,sys;"
        "from pathlib import Path;"
        "spec=importlib.util.spec_from_file_location('hybrid_atom_number', sys.argv[1]);"
        "mod=importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(mod);"
        "mod.process_directory(Path(sys.argv[2]))"
    )

    result = subprocess.run(
        [sys.executable, "-c", command_code, str(ATOM_NUMBERS_SCRIPT), str(directory)],
        check=True,
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    atom_numbers_path = directory / "atom_numbers.txt"
    if not atom_numbers_path.exists():
        raise FileNotFoundError(
            f"atom_number.py completed but did not produce {atom_numbers_path}. "
            "Check metadata do_scan setting and atom_number.py output mode."
        )

    atom_numbers = np.asarray(np.loadtxt(atom_numbers_path, comments="#"), dtype=float)
    return np.atleast_1d(atom_numbers).reshape(-1)


def find_metadata_file(images_directory: Path) -> Path:
    """Pick the newest metadata*.json from the parent directory."""
    candidates = list(images_directory.parent.glob("metadata*.json"))
    if not candidates:
        raise FileNotFoundError(
            f"No metadata*.json found in {images_directory.parent}"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_settings(metadata: dict) -> dict:
    """Extract camera and scan settings used by the TOF analysis."""
    camera = metadata["experimental_data"]["camera"]
    scanned_variables = metadata["scanned_variables"]
    if not scanned_variables:
        raise ValueError("metadata['scanned_variables'] is empty")

    scan = scanned_variables[0]
    camera_name = str(camera["camera_name"])
    pixels_per_mm = PIXELS_PER_MM_BY_CAMERA.get(camera_name)
    if pixels_per_mm is None:
        raise ValueError(f"Unsupported camera name for pixel calibration: {camera_name}")

    roi_enabled = bool(camera.get("roi_enabled", False))
    roi_center_px: tuple[float, float] | None = None
    if roi_enabled and ("roi_x_center" in camera) and ("roi_y_center" in camera):
        roi_center_px = (float(camera["roi_x_center"]), float(camera["roi_y_center"]))

    return {
        "camera_name": camera_name,
        "pixels_per_mm": float(pixels_per_mm),
        "roi_center_px": roi_center_px,
        "scan_min_ms": float(scan["min_val"]),
        "scan_max_ms": float(scan["max_val"]),
    }


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


def downsample_image(image: np.ndarray, factor: int) -> np.ndarray:
    """Downsample an image by averaging non-overlapping blocks."""
    if factor < 1:
        raise ValueError(f"FIT_DOWNSAMPLING_FACTOR must be >= 1, got {factor}")

    if factor == 1:
        return np.asarray(image, dtype=np.float32)

    image = np.asarray(image, dtype=np.float32)
    height, width = image.shape
    trimmed_height = height - (height % factor)
    trimmed_width = width - (width % factor)
    if trimmed_height <= 0 or trimmed_width <= 0:
        raise ValueError(
            f"Image too small for downsampling factor {factor}: shape={image.shape}"
        )

    trimmed = image[:trimmed_height, :trimmed_width]
    return trimmed.reshape(trimmed_height // factor, factor, trimmed_width // factor, factor).mean(axis=(1, 3))


def fit_gaussian_2d(
    image_no_background: np.ndarray,
    fit_gaussian: fitting.TRFLSQFitter,
    pixels_per_mm: float,
    initial_center_px: tuple[float, float] | None = None,
    previous_fit: models.Gaussian2D | None = None,
    width_px_ref: int = 2048,
    height_px_ref: int = 1536,
) -> tuple[list[float], models.Gaussian2D, float, float]:
    """Fit a 2D Gaussian and return params, sigma uncertainty, y-position uncertainty."""
    image_for_fit = downsample_image(image_no_background, FIT_DOWNSAMPLING_FACTOR)
    num_y, num_x = image_for_fit.shape
    x, y = np.meshgrid(
        np.linspace(0, width_px_ref, num_x),
        np.linspace(0, height_px_ref, num_y),
    )

    max_val = float(np.max(image_for_fit))
    if previous_fit is None:
        x_init = 0.5 * width_px_ref
        y_init = 0.5 * height_px_ref
        if initial_center_px is not None:
            # x/y grids are still in full-frame coordinates even when image is downsampled.
            x_init = float(np.clip(initial_center_px[0], 0.0, float(width_px_ref)))
            y_init = float(np.clip(initial_center_px[1], 0.0, float(height_px_ref)))
        p_init = models.Gaussian2D(
            amplitude=max_val,
            x_mean=x_init,
            y_mean=y_init,
            x_stddev=0.3 * width_px_ref,
            y_stddev=0.3 * height_px_ref,
            theta=1.6,
        )
    else:
        p_init = models.Gaussian2D(
            amplitude=max_val,
            x_mean=float(previous_fit.x_mean.value),
            y_mean=float(previous_fit.y_mean.value),
            x_stddev=max(abs(float(previous_fit.x_stddev.value)), 1.0),
            y_stddev=max(abs(float(previous_fit.y_stddev.value)), 1.0),
            theta=float(previous_fit.theta.value),
        )

    p_fit = fit_gaussian(p_init, x, y, image_for_fit)

    model_image = p_fit(x, y)
    residual = image_for_fit - model_image
    residual_rms = float(np.sqrt(np.mean(residual**2)))
    amplitude_abs = max(abs(float(p_fit.amplitude.value)), 1e-9)
    relative_residual = residual_rms / amplitude_abs

    width_m = width_px_ref / pixels_per_mm * 1e-3
    height_m = height_px_ref / pixels_per_mm * 1e-3
    x_stddev_m = abs(float(p_fit.x_stddev.value)) / width_px_ref * width_m
    y_stddev_m = abs(float(p_fit.y_stddev.value)) / height_px_ref * height_m
    sigma_m = float(np.sqrt(x_stddev_m * y_stddev_m))
    sigma_err_m = sigma_m * relative_residual
    y_mean_err_m = y_stddev_m * relative_residual

    return [
        float(p_fit.amplitude.value),
        float(p_fit.x_mean.value) / width_px_ref * width_m,
        float(p_fit.y_mean.value) / height_px_ref * height_m,
        x_stddev_m,
        y_stddev_m,
        float(p_fit.theta.value),
    ], p_fit, float(sigma_err_m), float(y_mean_err_m)


def process_images(
    image_pairs: list[tuple[Path, Path]],
    fit_gaussian: fitting.TRFLSQFitter,
    pixels_per_mm: float,
    initial_center_px: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Process all background/image pairs and return fit params, sigma/y errors."""
    fit_params: list[list[float]] = []
    sigma_errors_m: list[float] = []
    y_mean_errors_m: list[float] = []
    previous_fit: models.Gaussian2D | None = None

    for background_path, image_path in tqdm(image_pairs, desc="Processing TOF pairs"):
        image = read_tiff_fallback_safe(str(image_path))
        background = read_tiff_fallback_safe(str(background_path))
        image_no_background = image - background

        frame_fit_params, previous_fit, sigma_err_m, y_mean_err_m = fit_gaussian_2d(
            image_no_background,
            fit_gaussian,
            pixels_per_mm=pixels_per_mm,
            initial_center_px=initial_center_px if previous_fit is None else None,
            previous_fit=previous_fit,
        )
        fit_params.append(frame_fit_params)
        sigma_errors_m.append(sigma_err_m)
        y_mean_errors_m.append(y_mean_err_m)

    return (
        np.asarray(fit_params, dtype=float),
        np.asarray(sigma_errors_m, dtype=float),
        np.asarray(y_mean_errors_m, dtype=float),
    )


def fit_tof(
    scan_values_s: np.ndarray,
    fit_params: np.ndarray,
    sigma_errors_m: np.ndarray,
    fit_model: fitting.TRFLSQFitter,
) -> tuple[np.ndarray, models.custom_model]:
    """Fit cloud expansion model from Gaussian widths."""
    sigma_x = np.abs(fit_params[:, 3])
    sigma_y = np.abs(fit_params[:, 4])
    sigma_values = np.sqrt(sigma_x * sigma_y)

    valid = (
        np.isfinite(scan_values_s)
        & np.isfinite(sigma_values)
        & np.isfinite(sigma_errors_m)
        & (sigma_values > 0)
        & (sigma_errors_m > 0)
    )
    scan_fit = scan_values_s[valid]
    sigma_fit = sigma_values[valid]
    sigma_err_fit = sigma_errors_m[valid]
    if scan_fit.size < 3:
        raise ValueError("Not enough valid TOF points after filtering to run fit")

    err_floor = max(float(np.median(sigma_err_fit)) * 0.1, 1e-12)
    weights = 1.0 / np.maximum(sigma_err_fit, err_floor)

    model_init = expansion_model()
    model_init.sigma0.bounds = (0.0, None)
    model_init.T.bounds = (0.0, None)

    model_fit = fit_model(
        model_init,
        scan_fit,
        sigma_fit,
        weights=weights,
        filter_non_finite=True,
    )
    return sigma_values, model_fit


def fit_vertical_position(
    scan_values_s: np.ndarray,
    fit_params: np.ndarray,
    y_mean_errors_m: np.ndarray,
    fit_model: fitting.TRFLSQFitter,
) -> tuple[models.custom_model, float, float]:
    """Fit constrained vertical motion and return model plus weighted metrics."""
    y_values = np.asarray(fit_params[:, 2], dtype=float)
    valid = (
        np.isfinite(scan_values_s)
        & np.isfinite(y_values)
        & np.isfinite(y_mean_errors_m)
        & (y_mean_errors_m > 0)
    )
    t_fit = scan_values_s[valid]
    y_fit = y_values[valid]
    y_err_fit = y_mean_errors_m[valid]
    if t_fit.size < 3:
        raise ValueError("Not enough valid y-position points for parabola fit")

    err_floor = max(float(np.median(y_err_fit)) * 0.25, 1e-12)
    y_err_use = np.maximum(y_err_fit, err_floor)
    weights = 1.0 / y_err_use

    model_init = vertical_position_model()
    model_init.y0.value = float(np.median(y_fit))
    model_fit = fit_model(model_init, t_fit, y_fit, weights=weights, filter_non_finite=True)

    y_pred = np.asarray(model_fit(t_fit), dtype=float)
    w_r2, chi2_red = compute_weighted_fit_quality(y_fit, y_pred, y_err_use, n_params=2)
    return model_fit, w_r2, chi2_red


def process_directory(directory: Path) -> None:
    """Run complete TOF analysis for one image directory."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Image directory not found: {directory}")

    metadata_file = find_metadata_file(directory)
    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    settings = parse_settings(metadata)
    print(f"Processing {directory}")
    print(f"Using metadata file: {metadata_file.name}")
    print(f"Downsampling factor: {FIT_DOWNSAMPLING_FACTOR}")

    sorted_tifs = sort_tif_files(directory)
    image_pairs = make_background_image_pairs(sorted_tifs)

    fit_gaussian = fitting.TRFLSQFitter()
    fit_model = fitting.TRFLSQFitter()

    fit_params, sigma_errors_m, y_mean_errors_m = process_images(
        image_pairs,
        fit_gaussian,
        pixels_per_mm=settings["pixels_per_mm"],
        initial_center_px=settings["roi_center_px"],
    )

    atom_numbers = run_atom_number_subprocess(directory)
    if atom_numbers.size <= 0:
        raise ValueError("atom_number.py produced an empty atom_numbers.txt")

    n_points = min(len(image_pairs), fit_params.shape[0], atom_numbers.size)
    if n_points < len(image_pairs):
        print(
            f"Warning: point-count mismatch (pairs={len(image_pairs)}, fit={fit_params.shape[0]}, "
            f"atom_numbers={atom_numbers.size}); truncating TOF fit inputs to {n_points}"
        )

    fit_params = fit_params[:n_points]
    sigma_errors_m = sigma_errors_m[:n_points]
    y_mean_errors_m = y_mean_errors_m[:n_points]
    scan_values_ms = np.linspace(settings["scan_min_ms"], settings["scan_max_ms"], n_points)
    scan_values_s = scan_values_ms * 1e-3
    sigma_values, tof_model_fit = fit_tof(scan_values_s, fit_params, sigma_errors_m, fit_model)
    y_model_fit, y_w_r2, y_chi2_red = fit_vertical_position(
        scan_values_s,
        fit_params,
        y_mean_errors_m,
        fit_model,
    )

    fit_table = np.column_stack((scan_values_ms, fit_params, y_mean_errors_m))
    np.savetxt(
        directory / "fit_parameters.txt",
        fit_table,
        header="scan amplitude x_mean_m y_mean_m x_stddev_m y_stddev_m theta_rad y_mean_err_m",
    )

    tof_summary = np.array(
        [
            tof_model_fit.sigma0.value,
            tof_model_fit.T.value,
        ],
        dtype=float,
    )
    np.savetxt(
        directory / "tof_fit_parameters.txt",
        tof_summary,
        header="sigma0_m temperature_K",
    )

    np.savetxt(
        directory / "tof_sigma_vs_scan.txt",
        np.column_stack((scan_values_ms, sigma_values, sigma_errors_m)),
        header="scan sigma_m sigma_err_m",
    )

    y_fit_summary = np.array(
        [
            float(y_model_fit.y0.value),
            float(y_model_fit.a.value),
            float(y_w_r2),
            float(y_chi2_red),
        ],
        dtype=float,
    )
    np.savetxt(
        directory / "cloud_y_fit_parameters.txt",
        y_fit_summary,
        header="y0_m a_m_per_s2 weighted_r2 chi2_red",
    )

    print(
        "Saved: fit_parameters.txt, "
        "tof_fit_parameters.txt, tof_sigma_vs_scan.txt, cloud_y_fit_parameters.txt"
    )


if __name__ == "__main__":
    main()
