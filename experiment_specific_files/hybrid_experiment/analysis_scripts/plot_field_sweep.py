from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.widgets import Slider


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
TAKE_LAST_N = 1

INPUT_BASENAME = "field_sweep_results"
OUTPUT_PREFIX = "field_sweep_plot"

# Slider scans the last variable (index 2), while heatmaps are over variables 1 and 2.
SERIES_VARIABLE_INDEX = 2

SAVE_FIGURES = False
SHOW_FIGURES = True
ANIS_LOG_FLOOR = 1e-6


def load_target_directories(path_list_file: Path, take_last_n: int = 1) -> list[Path]:
    if not path_list_file.exists():
        raise FileNotFoundError(f"Path list file not found: {path_list_file}")

    with path_list_file.open("r", encoding="utf-8") as file:
        raw_dirs = [line.strip() for line in file if line.strip()]

    if not raw_dirs:
        raise ValueError(f"No directories found in {path_list_file}")

    return [Path(line) for line in raw_dirs][-take_last_n:]


def load_processed_data(directory: Path) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[str]]:
    npz_path = directory / f"{INPUT_BASENAME}.npz"
    meta_path = directory / f"{INPUT_BASENAME}_meta.json"

    if not npz_path.exists():
        raise FileNotFoundError(f"Missing processed data file: {npz_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing processed metadata file: {meta_path}")

    payload = np.load(npz_path)
    atom_grid = np.asarray(payload["atom_grid"], dtype=float)
    anis_grid = np.asarray(payload["anisotropy_grid"], dtype=float)
    axes = [
        np.asarray(payload["axis_0"], dtype=float),
        np.asarray(payload["axis_1"], dtype=float),
        np.asarray(payload["axis_2"], dtype=float),
    ]

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    variable_names = [str(x) for x in meta.get("variable_names", ["var0", "var1", "var2"])]
    if len(variable_names) != 3:
        raise ValueError(f"Expected 3 variable names, got {len(variable_names)}")

    if atom_grid.shape != anis_grid.shape:
        raise ValueError("atom_grid and anisotropy_grid shape mismatch")

    return atom_grid, anis_grid, axes, variable_names


def get_experiment_root(directory: Path) -> Path:
    """Return the experiment root above date/time/image folders."""
    return directory.parents[2]


def build_output_timestamp(directory: Path) -> str:
    """Build a TOF-style timestamp from the directory name when possible."""
    try:
        date_str = directory.parent.parent.name
        time_str = directory.parent.name
        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y_%m_%d_%H_%M_%S")
        return dt.strftime("%Y%m%d_%H%M%S")
    except Exception:
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def plot_directory(directory: Path) -> None:
    atom_grid, anis_grid, axes, variable_names = load_processed_data(directory)

    if atom_grid.ndim != 3:
        raise ValueError(f"Expected 3D grids, got shape {atom_grid.shape}")

    if SERIES_VARIABLE_INDEX not in (0, 1, 2):
        raise ValueError("SERIES_VARIABLE_INDEX must be 0, 1, or 2")

    x_idx = 0
    y_idx = 1
    x_axis = axes[x_idx]
    y_axis = axes[y_idx]
    series_axis = axes[SERIES_VARIABLE_INDEX]

    x_name = variable_names[x_idx]
    y_name = variable_names[y_idx]
    series_name = variable_names[SERIES_VARIABLE_INDEX]

    atom_vmin = float(np.nanmin(atom_grid))
    atom_vmax = float(np.nanmax(atom_grid))
    finite_positive_anis = anis_grid[np.isfinite(anis_grid) & (anis_grid > 0.0)]
    if finite_positive_anis.size == 0:
        anis_vmin = ANIS_LOG_FLOOR
        anis_vmax = 1.0
    else:
        anis_vmin = max(float(np.nanmin(finite_positive_anis)), ANIS_LOG_FLOOR)
        anis_vmax = max(float(np.nanmax(finite_positive_anis)), anis_vmin * 10.0)

    if atom_grid.shape[x_idx] != x_axis.size or atom_grid.shape[y_idx] != y_axis.size:
        raise ValueError(
            "Grid shape does not match expected first/second scanned variable axes"
        )

    def get_plot_slices(series_i: int) -> tuple[np.ndarray, np.ndarray]:
        # Raw slice has shape (len(axis_0), len(axis_1)); transpose to (y, x) for imshow.
        atom_slice = np.asarray(np.take(atom_grid, series_i, axis=SERIES_VARIABLE_INDEX), dtype=float).T
        anis_slice = np.asarray(np.take(anis_grid, series_i, axis=SERIES_VARIABLE_INDEX), dtype=float).T
        anis_plot = np.where(np.isfinite(anis_slice) & (anis_slice > 0.0), anis_slice, np.nan)
        return atom_slice, anis_plot

    extent = [
        float(np.min(x_axis)),
        float(np.max(x_axis)),
        float(np.min(y_axis)),
        float(np.max(y_axis)),
    ]

    initial_index = 0
    initial_series_value = float(series_axis[initial_index])
    atom_slice_0, anis_plot_0 = get_plot_slices(initial_index)

    fig, axs = plt.subplots(1, 2, figsize=(14, 5), dpi=120)
    plt.subplots_adjust(bottom=0.18)

    im0 = axs[0].imshow(
        atom_slice_0,
        origin="lower",
        aspect="auto",
        extent=extent,
        interpolation="nearest",
        vmin=atom_vmin,
        vmax=atom_vmax,
    )
    axs[0].set_title(f"Atom count, {series_name}={initial_series_value:.4g}")
    axs[0].set_xlabel(x_name)
    axs[0].set_ylabel(y_name)
    cb0 = fig.colorbar(im0, ax=axs[0])
    cb0.set_label("Atom count")

    im1 = axs[1].imshow(
        anis_plot_0,
        origin="lower",
        aspect="auto",
        extent=extent,
        interpolation="nearest",
        norm=LogNorm(vmin=anis_vmin, vmax=anis_vmax),
    )
    axs[1].set_title(f"|sigma_x - sigma_y| / (sigma_x + sigma_y), {series_name}={initial_series_value:.4g}")
    axs[1].set_xlabel(x_name)
    axs[1].set_ylabel(y_name)
    cb1 = fig.colorbar(im1, ax=axs[1])
    cb1.set_label("Anisotropy (log scale)")

    fig.suptitle(str(directory))

    slider_ax = fig.add_axes([0.15, 0.06, 0.7, 0.03])
    slider = Slider(
        ax=slider_ax,
        label=f"{series_name} index",
        valmin=0,
        valmax=max(series_axis.size - 1, 0),
        valinit=initial_index,
        valstep=1,
    )

    def update(_value: float) -> None:
        i_series = int(slider.val)
        series_value = float(series_axis[i_series])
        atom_slice, anis_plot = get_plot_slices(i_series)
        im0.set_data(atom_slice)
        im1.set_data(anis_plot)
        axs[0].set_title(f"Atom count, {series_name}={series_value:.4g}")
        axs[1].set_title(
            f"|sigma_x - sigma_y| / (sigma_x + sigma_y), {series_name}={series_value:.4g}"
        )
        fig.canvas.draw_idle()

    slider.on_changed(update)

    data_timestamp = build_output_timestamp(directory)
    out_path = get_experiment_root(directory) / f"{OUTPUT_PREFIX}_{series_name}_{data_timestamp}.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path}")

    if SHOW_FIGURES:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=TAKE_LAST_N)

    for directory in target_directories:
        plot_directory(directory)


if __name__ == "__main__":
    main()
