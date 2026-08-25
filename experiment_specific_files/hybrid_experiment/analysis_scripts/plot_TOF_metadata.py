from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.modeling.models import custom_model


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
INCLUDE_CLOUD_Y_PLOT = False


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        try:
            directory = Path(directory)
            metadata_file = find_metadata_file(directory)

            with metadata_file.open("r", encoding="utf-8") as file:
                metadata = json.load(file)

            scanned_variables = get_scanned_variables(metadata)
            scan_info = scanned_variables[0]
            scan_label = metadata.get("experimental_data", {}).get("comment", "Scan value")
            info_text = build_info_text(scan_info)

            atom_numbers = load_atom_numbers_for_tof_plot(directory, scanned_variables)
            fit_params = load_required_table(directory / "fit_parameters.txt", expected_cols=7, table_name="fit_parameters")
            sigma_path = directory / "tof_sigma_vs_scan.txt"
            sigma_table = np.loadtxt(sigma_path) if sigma_path.exists() else None
            if sigma_table is not None:
                sigma_table = np.atleast_2d(sigma_table)

            tof_fit_path = directory / "tof_fit_parameters.txt"
            tof_fit_table = np.loadtxt(tof_fit_path) if tof_fit_path.exists() else None
            tof_fit_x_path = directory / "tof_fit_parameters_x.txt"
            tof_fit_x_table = np.loadtxt(tof_fit_x_path) if tof_fit_x_path.exists() else None
            tof_fit_y_path = directory / "tof_fit_parameters_y.txt"
            tof_fit_y_table = np.loadtxt(tof_fit_y_path) if tof_fit_y_path.exists() else None
            y_fit_path = directory / "cloud_y_fit_parameters.txt"
            y_fit_table = np.loadtxt(y_fit_path) if y_fit_path.exists() else None

            sigma_x_path = directory / "tof_sigma_x_vs_scan.txt"
            sigma_x_table = np.loadtxt(sigma_x_path) if sigma_x_path.exists() else None
            if sigma_x_table is not None:
                sigma_x_table = np.atleast_2d(sigma_x_table)

            sigma_y_path = directory / "tof_sigma_y_vs_scan.txt"
            sigma_y_table = np.loadtxt(sigma_y_path) if sigma_y_path.exists() else None
            if sigma_y_table is not None:
                sigma_y_table = np.atleast_2d(sigma_y_table)

            analysis_method = "gaussian"
            analysis_method_path = directory / "tof_analysis_method.txt"
            if analysis_method_path.exists():
                analysis_method = analysis_method_path.read_text(encoding="utf-8").strip().lower()
            if analysis_method not in {"gaussian", "moments", "separate_gaussians"}:
                analysis_method = "gaussian"

            print(f"Plotting {directory}")
            print(f"Using metadata file: {metadata_file.name}")

            nrows = 3 if INCLUDE_CLOUD_Y_PLOT else 2
            fig_height = 14 if INCLUDE_CLOUD_Y_PLOT else 10
            fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(14, fig_height), dpi=100)
            axes = np.atleast_1d(axes)
            fig.suptitle(str(directory))
            maximize_figure_window(fig)

            plot_atom_number(axes[0], directory, scan_label, atom_numbers, info_text)
            if INCLUDE_CLOUD_Y_PLOT:
                plot_cloud_position(axes[1], scan_label, fit_params, y_fit_table, info_text)
                if analysis_method == "separate_gaussians":
                    plot_sigma_vs_scan_separate(
                        axes[2],
                        scan_label,
                        sigma_x_table,
                        sigma_y_table,
                        tof_fit_x_table,
                        tof_fit_y_table,
                        info_text,
                    )
                else:
                    plot_sigma_vs_scan(axes[2], directory, scan_label, fit_params, sigma_table, tof_fit_table, analysis_method, info_text)
                axes[0].tick_params(labelbottom=False)
                axes[1].tick_params(labelbottom=False)
            else:
                if analysis_method == "separate_gaussians":
                    plot_sigma_vs_scan_separate(
                        axes[1],
                        scan_label,
                        sigma_x_table,
                        sigma_y_table,
                        tof_fit_x_table,
                        tof_fit_y_table,
                        info_text,
                    )
                else:
                    plot_sigma_vs_scan(axes[1], directory, scan_label, fit_params, sigma_table, tof_fit_table, analysis_method, info_text)
                axes[0].tick_params(labelbottom=False)

            fig.tight_layout(rect=(0, 0, 1, 0.98))
            fig.subplots_adjust(hspace=0.0)

            try:
                # Expected path tail: .../TOF/YYYY_MM_DD/HH_MM_SS/<axis>
                date_str = directory.parent.parent.name
                time_str = directory.parent.name
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y_%m_%d_%H_%M_%S")
                data_timestamp = dt.strftime("%Y%m%d_%H%M%S")
            except Exception:
                data_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_path = directory.parents[2] / "images" / f"tof_summary_{data_timestamp}.png"
            output_path.parent.mkdir(exist_ok=True)
            fig.savefig(output_path, dpi=150)
            print(f"Saved figure: {output_path}")
        except KeyboardInterrupt:
            print("Stopped by user")
            break
        except Exception as exc:
            print(f"Skipping {directory}: {exc}")

    plt.show()


@custom_model
def expansion_model(t, sigma0=0.001, T=100e-6):
    """Cloud width after time-of-flight expansion."""
    return np.sqrt(sigma0**2 + (1.38 / 1.443) * 1e2 * T * t**2)


@custom_model
def vertical_position_model(t, y0=0.0, a=9.81):
    """Constrained vertical motion model with zero linear term: y(t)=y0+0.5*a*t^2."""
    return y0 + 0.5 * a * t**2


def maximize_figure_window(fig) -> None:
    """Best-effort maximize for interactive backends."""
    try:
        manager = getattr(fig.canvas, "manager", None)
        if manager is None:
            return

        window = getattr(manager, "window", None)
        if window is not None:
            if hasattr(window, "showMaximized"):
                window.showMaximized()
                return
            if hasattr(window, "state"):
                window.state("zoomed")
                return

        if hasattr(manager, "full_screen_toggle"):
            manager.full_screen_toggle()
    except Exception:
        pass


def load_target_directories(path_list_file: Path, take_last_n: int = 1) -> list[Path]:
    """Load target image directories from a path list file."""
    if not path_list_file.exists():
        raise FileNotFoundError(f"Path list file not found: {path_list_file}")

    with path_list_file.open("r", encoding="utf-8") as file:
        raw_dirs = [line.strip() for line in file if line.strip()]

    if not raw_dirs:
        raise ValueError(f"No directories found in {path_list_file}")

    return [Path(line) for line in raw_dirs][-take_last_n:]


def find_metadata_file(images_directory: Path) -> Path:
    """Pick the newest metadata*.json from the parent directory."""
    candidates = list(images_directory.parent.glob("metadata*.json"))
    if not candidates:
        raise FileNotFoundError(
            f"No metadata*.json found in {images_directory.parent}"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_required_table(path: Path, expected_cols: int, table_name: str) -> np.ndarray:
    """Load a whitespace table and normalize shape for single-row files."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {table_name}: {path}")

    data = np.loadtxt(path)
    data = np.atleast_2d(data)
    if data.shape[1] < expected_cols:
        raise ValueError(
            f"{table_name} has {data.shape[1]} columns, expected at least {expected_cols}"
        )
    return data


def get_scanned_variables(metadata: dict) -> list[dict]:
    """Return scanned variables sorted by Dim."""
    scanned_variables = metadata.get("scanned_variables", [])
    if not scanned_variables:
        raise ValueError("metadata['scanned_variables'] is empty")
    return sorted(scanned_variables, key=lambda item: int(item["Dim"]))


def build_scan_axes(scanned_variables: list[dict]) -> list[np.ndarray]:
    """Create one coordinate axis per scanned variable."""
    axes: list[np.ndarray] = []
    for variable in scanned_variables:
        steps = int(variable["num_scan_steps"])
        axes.append(np.linspace(float(variable["min_val"]), float(variable["max_val"]), steps))
    return axes


def load_atom_numbers_for_tof_plot(directory: Path, scanned_variables: list[dict]) -> np.ndarray:
    """Load atom_numbers and normalize to two columns [atom_number, scan_value]."""
    path = directory / "atom_numbers.txt"
    if not path.exists():
        raise FileNotFoundError(f"Missing atom_numbers: {path}")

    raw = np.asarray(np.loadtxt(path, comments="#"), dtype=float)
    if raw.ndim == 0:
        raw = raw.reshape(1)

    if raw.ndim == 1:
        atom_values = raw.reshape(-1)
        scan_axis = np.asarray(build_scan_axes(scanned_variables)[0], dtype=float).reshape(-1)
        if scan_axis.size != atom_values.size:
            # Keep plotting robust when counts were truncated upstream.
            scan_axis = np.linspace(float(scan_axis[0]), float(scan_axis[-1]), atom_values.size)
        return np.column_stack((atom_values, scan_axis))

    data = np.atleast_2d(raw)
    if data.shape[1] < 2:
        raise ValueError(f"atom_numbers has {data.shape[1]} columns, expected 1 or at least 2")
    return data[:, :2]


def build_info_text(scan_info: dict) -> str:
    """Build annotation text from scan settings."""
    text_lines = []
    for key, value in scan_info.items():
        if key in {"min_val", "max_val", "scan"}:
            continue
        if key == "text":
            text_lines.append(str(value))
            continue

        if isinstance(value, (int, float)):
            if key.startswith("t"):
                text_lines.append(f"{key} = {value * 1e3:.3f} ms")
            else:
                text_lines.append(f"{key} = {value:.4g}")
        else:
            text_lines.append(f"{key} = {value}")

    return "\n".join(text_lines)


def compute_weighted_fit_quality(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_err: np.ndarray,
    n_params: int = 2,
) -> tuple[float, float]:
    """Return (weighted_R2, reduced_chi2) using per-point uncertainties."""
    valid = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & np.isfinite(y_err)
        & (y_err > 0)
    )
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
    reduced_chi2 = float(np.sum(((y_t - y_p) / s) ** 2) / dof)
    return weighted_r2, reduced_chi2


def plot_atom_number(
    ax,
    directory: Path,
    scan_label: str,
    atom_numbers: np.ndarray,
    info_text: str,
) -> None:
    atom_millions = atom_numbers[:, 0] * 1e-6
    ax.plot(atom_numbers[:, 1], atom_millions, "-o", ms=3, lw=1)
    # ax.set_ylim((0, None))
    ax.set_xlim((0.9 * np.min(atom_numbers[:, 1]), 1.1 * np.max(atom_numbers[:, 1])))
    ax.set_xlabel("")
    ax.set_ylabel("Atom number (million)")
    ax.minorticks_on()
    ax.grid(True, which="both", alpha=0.35)

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def plot_sigma_vs_scan(
    ax,
    directory: Path,
    scan_label: str,
    fit_params: np.ndarray,
    sigma_table: np.ndarray | None,
    tof_fit_table: np.ndarray | None,
    analysis_method: str,
    info_text: str,
) -> None:
    scan_ms = fit_params[:, 0]
    scan_s = scan_ms * 1e-3
    sigma = np.sqrt(np.abs(fit_params[:, 4]) * np.abs(fit_params[:, 5]))
    sigma_err = None
    if sigma_table is not None and sigma_table.shape[1] >= 3:
        sigma_err = np.asarray(sigma_table[:, 2], dtype=float)

    if analysis_method == "separate_gaussians":
        method_label = "Separate X/Y Gaussian fit"
    elif analysis_method == "gaussian":
        method_label = "Gaussian fit"
    else:
        method_label = "Moments"

    if sigma_err is not None and sigma_err.shape[0] == sigma.shape[0]:
        ax.errorbar(
            scan_ms,
            sigma * 1e3,
            yerr=sigma_err * 1e3,
            fmt="o",
            ms=4,
            lw=1,
            capsize=3,
            label=f"From {method_label}",
        )
    else:
        ax.plot(scan_ms, sigma * 1e3, "o", ms=4, lw=1, label=f"From {method_label}")

    if tof_fit_table is not None and tof_fit_table.size >= 2:
        sigma0, temperature = float(tof_fit_table[0]), float(tof_fit_table[1])
        model = expansion_model(sigma0=sigma0, T=temperature)
        dense_scan_ms = np.linspace(np.min(scan_ms), np.max(scan_ms), 200)
        sigma_pred = np.asarray(model(scan_s), dtype=float)

        if sigma_err is not None and sigma_err.shape[0] == sigma.shape[0]:
            w_r2, red_chi2 = compute_weighted_fit_quality(sigma, sigma_pred, sigma_err, n_params=2)
            if np.isfinite(w_r2) and np.isfinite(red_chi2):
                fit_label = (
                    f"Weighted TOF fit (T={temperature * 1e6:.1f} uK, "
                    f"wR^2={w_r2:.4f}, chi2_red={red_chi2:.3f})"
                )
            elif np.isfinite(w_r2):
                fit_label = f"Weighted TOF fit (T={temperature * 1e6:.1f} uK, wR^2={w_r2:.4f})"
            else:
                fit_label = f"Weighted TOF fit (T={temperature * 1e6:.1f} uK)"
        else:
            valid = np.isfinite(sigma) & np.isfinite(sigma_pred)
            sigma_valid = sigma[valid]
            sigma_pred_valid = sigma_pred[valid]
            if sigma_valid.size >= 2:
                residual = sigma_valid - sigma_pred_valid
                ss_res = float(np.sum(residual**2))
                ss_tot = float(np.sum((sigma_valid - np.mean(sigma_valid)) ** 2))
                r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
            else:
                r_squared = np.nan
            if np.isfinite(r_squared):
                fit_label = f"Weighted TOF fit (T={temperature * 1e6:.1f} uK, R^2={r_squared:.4f})"
            else:
                fit_label = f"Weighted TOF fit (T={temperature * 1e6:.1f} uK, R^2=n/a)"

        ax.plot(dense_scan_ms, model(dense_scan_ms * 1e-3) * 1e3, "-", lw=2, label=fit_label)

    # ax.set_ylim((0, None))
    ax.set_xlim((0.9 * np.min(scan_ms), 1.1 * np.max(scan_ms)))
    ax.set_xlabel(scan_label)
    ax.set_ylabel("Cloud width sigma (mm)")
    ax.minorticks_on()
    ax.grid(True, which="both", alpha=0.35)
    ax.legend()

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def plot_sigma_component(
    ax,
    scan_ms: np.ndarray,
    sigma_table: np.ndarray | None,
    fit_table: np.ndarray | None,
    component_label: str,
    color: str,
) -> None:
    sigma = sigma_table[:, 1] if sigma_table is not None and sigma_table.shape[1] >= 2 else None
    sigma_err = None
    if sigma_table is not None and sigma_table.shape[1] >= 3:
        sigma_err = np.asarray(sigma_table[:, 2], dtype=float)

    if sigma is None:
        return

    sigma = np.asarray(sigma, dtype=float)
    if sigma_err is not None and sigma_err.shape[0] == sigma.shape[0]:
        ax.errorbar(scan_ms, sigma * 1e3, yerr=sigma_err * 1e3, fmt="o", ms=4, lw=1, capsize=3, color=color, label=component_label)
    else:
        ax.plot(scan_ms, sigma * 1e3, "o", ms=4, lw=1, color=color, label=component_label)

    if fit_table is not None and fit_table.size >= 2:
        sigma0, temperature = float(fit_table[0]), float(fit_table[1])
        model = expansion_model(sigma0=sigma0, T=temperature)
        dense_scan_ms = np.linspace(np.min(scan_ms), np.max(scan_ms), 200)
        ax.plot(dense_scan_ms, model(dense_scan_ms * 1e-3) * 1e3, "-", lw=2, color=color, label=f"{component_label} fit (T={temperature * 1e6:.1f} uK)")


def plot_sigma_vs_scan_separate(
    ax,
    scan_label: str,
    sigma_x_table: np.ndarray | None,
    sigma_y_table: np.ndarray | None,
    tof_fit_x_table: np.ndarray | None,
    tof_fit_y_table: np.ndarray | None,
    info_text: str,
) -> None:
    """Plot X and Y TOF widths and separate temperature fits on one axis."""
    if sigma_x_table is None or sigma_y_table is None:
        ax.text(0.5, 0.5, "Missing separate TOF sigma files", transform=ax.transAxes, ha="center", va="center")
        return

    scan_ms = np.asarray(sigma_x_table[:, 0], dtype=float)
    plot_sigma_component(ax, scan_ms, sigma_x_table, tof_fit_x_table, "X width", "tab:blue")
    plot_sigma_component(ax, np.asarray(sigma_y_table[:, 0], dtype=float), sigma_y_table, tof_fit_y_table, "Y width", "tab:orange")

    ax.set_xlim((0.9 * np.min(scan_ms), 1.1 * np.max(scan_ms)))
    ax.set_xlabel(scan_label)
    ax.set_ylabel("Cloud width sigma (mm)")
    ax.minorticks_on()
    ax.grid(True, which="both", alpha=0.35)
    ax.legend()

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def plot_cloud_position(
    ax,
    scan_label: str,
    fit_params: np.ndarray,
    y_fit_table: np.ndarray | None,
    info_text: str,
) -> None:
    scan = fit_params[:, 0]
    time_s = scan * 1e-3
    y_mean_m = fit_params[:, 3]
    y_err_m = None
    if fit_params.shape[1] >= 8:
        y_err_m = np.asarray(fit_params[:, 7], dtype=float)

    if y_err_m is not None and y_err_m.shape[0] == y_mean_m.shape[0]:
        ax.errorbar(
            scan,
            y_mean_m * 1e3,
            yerr=y_err_m * 1e3,
            fmt="o",
            ms=4,
            lw=1,
            capsize=3,
            label="Cloud y-position",
        )
    else:
        ax.plot(scan, y_mean_m * 1e3, "o", ms=4, lw=1, label="Cloud y-position")

    if y_fit_table is not None and y_fit_table.size >= 4:
        y0 = float(y_fit_table[0])
        accel = float(y_fit_table[1])
        w_r2 = float(y_fit_table[2])
        chi2_red = float(y_fit_table[3])

        model = vertical_position_model(y0=y0, a=accel)
        t_dense = np.linspace(np.min(time_s), np.max(time_s), 300)
        y_dense = np.asarray(model(t_dense), dtype=float)

        if np.isfinite(w_r2) and np.isfinite(chi2_red):
            fit_label = (
                f"Weighted parabola, a1=0 (a={accel:.3f} m/s^2, "
                f"wR^2={w_r2:.4f}, chi2_red={chi2_red:.3f})"
            )
        elif np.isfinite(w_r2):
            fit_label = f"Weighted parabola, a1=0 (a={accel:.3f} m/s^2, wR^2={w_r2:.4f})"
        else:
            fit_label = f"Weighted parabola, a1=0 (a={accel:.3f} m/s^2)"

        ax.plot(t_dense * 1e3, y_dense * 1e3, "-", lw=2, label=fit_label)

    # ax.set_ylim((0, None))
    ax.set_xlim((0.9 * np.min(scan), 1.1 * np.max(scan)))
    ax.set_xlabel("")
    ax.set_ylabel("Cloud y-position (mm)")
    ax.minorticks_on()
    ax.grid(True, which="both", alpha=0.35)
    ax.legend()

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


if __name__ == "__main__":
    main()
