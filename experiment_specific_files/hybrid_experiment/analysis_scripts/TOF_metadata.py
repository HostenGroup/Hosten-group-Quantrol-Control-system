from __future__ import annotations

import importlib.util
import json
import re
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

ATOM_COUNT_FILE = (
    Path(__file__).resolve().parents[1]
    / "experiment_specific_files"
    / "hybrid_experiment"
    / "atom_count.py"
)


def load_atom_count_function():
    """Load atom_count() from the hybrid_experiment source file."""
    if not ATOM_COUNT_FILE.exists():
        raise FileNotFoundError(f"atom_count source not found: {ATOM_COUNT_FILE}")

    spec = importlib.util.spec_from_file_location("hybrid_atom_count", ATOM_COUNT_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from {ATOM_COUNT_FILE}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.atom_count


atom_count = load_atom_count_function()


# All values are in SI units unless otherwise noted.
DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
ANALYSIS_METHOD = "gaussian"  # Supported: "moments", "gaussian"


@custom_model
def expansion_model(t, sigma0=0.001, T=100e-6):
    """Cloud width after time-of-flight expansion."""
    return np.sqrt(sigma0**2 + (1.38 / 1.443) * 1e2 * T * t**2)


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
    return {
        "gain_db": float(camera["gain_db"]),
        "exposure_time_s": float(camera["exposure_time_ms"]) * 1e-3,
        "pixel_format": camera["format_name"],
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


def fit_gaussian_2d(
    image_no_background: np.ndarray,
    fit_gaussian: fitting.TRFLSQFitter,
    previous_fit: models.Gaussian2D | None = None,
    width_px_ref: int = 2048,
    height_px_ref: int = 1536,
) -> tuple[list[float], models.Gaussian2D, float, float]:
    """Fit a 2D Gaussian and return params, sigma uncertainty, y-position uncertainty."""
    num_y, num_x = image_no_background.shape
    x, y = np.meshgrid(
        np.linspace(0, width_px_ref, num_x),
        np.linspace(0, height_px_ref, num_y),
    )

    max_val = float(np.max(image_no_background))
    if previous_fit is None:
        p_init = models.Gaussian2D(
            amplitude=max_val,
            x_mean=0.5 * width_px_ref,
            y_mean=0.5 * height_px_ref,
            x_stddev=0.1 * width_px_ref,
            y_stddev=0.1 * height_px_ref,
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

    p_fit = fit_gaussian(p_init, x, y, image_no_background)

    model_image = p_fit(x, y)
    residual = image_no_background - model_image
    residual_rms = float(np.sqrt(np.mean(residual**2)))
    amplitude_abs = max(abs(float(p_fit.amplitude.value)), 1e-9)
    relative_residual = residual_rms / amplitude_abs

    x_stddev_m = abs(float(p_fit.x_stddev.value)) / width_px_ref * 8e-3
    y_stddev_m = abs(float(p_fit.y_stddev.value)) / height_px_ref * 6e-3
    sigma_m = float(np.sqrt(x_stddev_m * y_stddev_m))
    sigma_err_m = sigma_m * relative_residual
    y_mean_err_m = y_stddev_m * relative_residual

    return [
        float(p_fit.amplitude.value),
        float(p_fit.x_mean.value) / width_px_ref * 8e-3,
        float(p_fit.y_mean.value) / height_px_ref * 6e-3,
        x_stddev_m,
        y_stddev_m,
        float(p_fit.theta.value),
    ], p_fit, float(sigma_err_m), float(y_mean_err_m)


def moments_2d_parameters(
    image_no_background: np.ndarray,
    width_px_ref: int = 2048,
    height_px_ref: int = 1536,
) -> tuple[list[float], float, float]:
    """Estimate cloud parameters from image moments and return sigma/y uncertainties."""
    # Use only positive signal for moments to avoid subtraction noise dominating weights.
    weights = np.clip(np.asarray(image_no_background, dtype=np.float64), 0.0, None)
    if not np.any(weights > 0.0):
        weights = np.abs(np.asarray(image_no_background, dtype=np.float64))

    total_w = float(np.sum(weights))
    if total_w <= 0.0:
        return [0.0, 0.0, 0.0, 1e-9, 1e-9, 0.0], 0.0, 0.0

    num_y, num_x = weights.shape
    x_pix = np.linspace(0.0, width_px_ref, num_x)
    y_pix = np.linspace(0.0, height_px_ref, num_y)
    x_grid_pix, y_grid_pix = np.meshgrid(x_pix, y_pix)

    x_mean_pix = float(np.sum(weights * x_grid_pix) / total_w)
    y_mean_pix = float(np.sum(weights * y_grid_pix) / total_w)

    dx = x_grid_pix - x_mean_pix
    dy = y_grid_pix - y_mean_pix
    var_x_pix2 = float(np.sum(weights * dx * dx) / total_w)
    var_y_pix2 = float(np.sum(weights * dy * dy) / total_w)
    cov_xy_pix2 = float(np.sum(weights * dx * dy) / total_w)

    cov = np.array(
        [[var_x_pix2, cov_xy_pix2], [cov_xy_pix2, var_y_pix2]],
        dtype=np.float64,
    )
    eigvals = np.linalg.eigvalsh(cov)
    eigvals = np.maximum(eigvals, 1e-12)
    std_major_pix = float(np.sqrt(eigvals[1]))
    std_minor_pix = float(np.sqrt(eigvals[0]))
    theta = 0.5 * float(np.arctan2(2.0 * cov_xy_pix2, var_x_pix2 - var_y_pix2))

    x_mean_m = x_mean_pix / width_px_ref * 8e-3
    y_mean_m = y_mean_pix / height_px_ref * 6e-3
    x_stddev_m = std_major_pix / width_px_ref * 8e-3
    y_stddev_m = std_minor_pix / height_px_ref * 6e-3

    sigma_m = float(np.sqrt(x_stddev_m * y_stddev_m))
    # Effective sample size based on moment weights for a simple uncertainty proxy.
    n_eff = float((total_w**2) / max(np.sum(weights**2), 1e-12))
    sigma_err_m = sigma_m / max(np.sqrt(n_eff), 1.0)
    y_mean_err_m = y_stddev_m / max(np.sqrt(n_eff), 1.0)

    params = [
        float(np.max(image_no_background)),
        x_mean_m,
        y_mean_m,
        x_stddev_m,
        y_stddev_m,
        theta,
    ]
    return params, sigma_err_m, y_mean_err_m


def process_images(
    image_pairs: list[tuple[Path, Path]],
    fit_gaussian: fitting.TRFLSQFitter,
    analysis_method: str = "moments",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Process all background/image pairs and return counts, fit params, sigma/y errors."""
    counts: list[float] = []
    fit_params: list[list[float]] = []
    sigma_errors_m: list[float] = []
    y_mean_errors_m: list[float] = []
    previous_fit: models.Gaussian2D | None = None
    method = analysis_method.strip().lower()
    if method not in {"moments", "gaussian"}:
        raise ValueError(f"Unsupported ANALYSIS_METHOD: {analysis_method}")

    for background_path, image_path in tqdm(image_pairs, desc="Processing TOF pairs"):
        image = read_tiff_fallback_safe(str(image_path))
        background = read_tiff_fallback_safe(str(background_path))
        image_no_background = image - background

        counts.append(float(np.sum(image_no_background)))
        if method == "gaussian":
            frame_fit_params, previous_fit, sigma_err_m, y_mean_err_m = fit_gaussian_2d(
                image_no_background,
                fit_gaussian,
                previous_fit=previous_fit,
            )
        else:
            frame_fit_params, sigma_err_m, y_mean_err_m = moments_2d_parameters(image_no_background)
        fit_params.append(frame_fit_params)
        sigma_errors_m.append(sigma_err_m)
        y_mean_errors_m.append(y_mean_err_m)

    return (
        np.asarray(counts, dtype=float),
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


def save_outputs(
    output_directory: Path,
    scan_values: np.ndarray,
    atom_numbers: np.ndarray,
    fit_params: np.ndarray,
    y_mean_errors_m: np.ndarray,
    sigma_values: np.ndarray,
    sigma_errors_m: np.ndarray,
    analysis_method: str,
    tof_model_fit,
    y_model_fit,
    y_w_r2: float,
    y_chi2_red: float,
) -> None:
    """Save atom numbers, Gaussian fit parameters, and TOF fit summary."""
    atom_table = np.column_stack((atom_numbers, scan_values))
    np.savetxt(
        output_directory / "atom_numbers.txt",
        atom_table,
        header="atom_number scan_value",
    )

    fit_table = np.column_stack((scan_values, fit_params, y_mean_errors_m))
    np.savetxt(
        output_directory / "fit_parameters.txt",
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
        output_directory / "tof_fit_parameters.txt",
        tof_summary,
        header="sigma0_m temperature_K",
    )

    np.savetxt(
        output_directory / "tof_sigma_vs_scan.txt",
        np.column_stack((scan_values, sigma_values, sigma_errors_m)),
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
        output_directory / "cloud_y_fit_parameters.txt",
        y_fit_summary,
        header="y0_m a_m_per_s2 weighted_r2 chi2_red",
    )

    with (output_directory / "tof_analysis_method.txt").open("w", encoding="utf-8") as file:
        file.write(f"{analysis_method.strip().lower()}\n")


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
    print(f"Analysis method: {ANALYSIS_METHOD}")

    sorted_tifs = sort_tif_files(directory)
    image_pairs = make_background_image_pairs(sorted_tifs)

    fit_gaussian = fitting.TRFLSQFitter()
    fit_model = fitting.TRFLSQFitter()

    counts, fit_params, sigma_errors_m, y_mean_errors_m = process_images(
        image_pairs,
        fit_gaussian,
        analysis_method=ANALYSIS_METHOD,
    )
    scan_values_ms = np.linspace(settings["scan_min_ms"], settings["scan_max_ms"], len(image_pairs))
    scan_values_s = scan_values_ms * 1e-3
    sigma_values, tof_model_fit = fit_tof(scan_values_s, fit_params, sigma_errors_m, fit_model)
    y_model_fit, y_w_r2, y_chi2_red = fit_vertical_position(
        scan_values_s,
        fit_params,
        y_mean_errors_m,
        fit_model,
    )

    atom_numbers = np.asarray(
        np.vectorize(atom_count)(
            counts,
            settings["gain_db"],
            settings["exposure_time_s"],
            settings["pixel_format"],
        ),
        dtype=float,
    )

    save_outputs(
        output_directory=directory,
        scan_values=scan_values_ms,
        atom_numbers=atom_numbers,
        fit_params=fit_params,
        y_mean_errors_m=y_mean_errors_m,
        sigma_values=sigma_values,
        sigma_errors_m=sigma_errors_m,
        analysis_method=ANALYSIS_METHOD,
        tof_model_fit=tof_model_fit,
        y_model_fit=y_model_fit,
        y_w_r2=y_w_r2,
        y_chi2_red=y_chi2_red,
    )

    print(
        "Saved: atom_numbers.txt, fit_parameters.txt, "
        "tof_fit_parameters.txt, tof_sigma_vs_scan.txt, cloud_y_fit_parameters.txt"
    )


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        process_directory(directory)


if __name__ == "__main__":
    main()
