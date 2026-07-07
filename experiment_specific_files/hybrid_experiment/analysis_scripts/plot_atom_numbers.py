from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
ENABLE_PARABOLA_FIT = False
NUMBERS_TO_LAST_TO_USE = 0
MOVING_AVERAGE_WINDOW = 5
ENABLE_ERROR_BARS = True
ENABLE_SNR = False


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1 + NUMBERS_TO_LAST_TO_USE)

    for directory in target_directories:
        try:
            process_directory(directory)
        except KeyboardInterrupt:
            print("Stopped by user")
            break
        except Exception as exc:
            print(f"Skipping {directory}: {exc}")

    plt.show()


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


def parse_header_value(header_lines: list[str], key: str) -> str:
    prefix = f"{key}:"
    for line in header_lines:
        cleaned = line.lstrip("#").strip()
        if cleaned.startswith(prefix):
            return cleaned[len(prefix):].strip()
    raise ValueError(f"Missing {key} in atom_numbers.txt header")


def parse_shape_text(shape_text: str) -> tuple[int, ...]:
    parts = [part.strip() for part in shape_text.split(",") if part.strip()]
    if not parts:
        raise ValueError("Empty shape in atom_numbers.txt header")
    return tuple(int(part) for part in parts)


def load_atom_number_tensor(path: Path) -> tuple[np.ndarray, tuple[int, ...], int, str]:
    """Load the flattened atom-number tensor and reconstruct its saved shape."""
    if not path.exists():
        raise FileNotFoundError(f"Missing atom_numbers file: {path}")

    with path.open("r", encoding="utf-8") as file:
        header_lines = [line.strip() for line in file if line.lstrip().startswith("#")]

    flat_values = np.atleast_1d(np.loadtxt(path, comments="#", ndmin=1)).astype(float)
    if header_lines:
        data_shape = parse_shape_text(parse_header_value(header_lines, "data_shape"))
        scan_shape = parse_shape_text(parse_header_value(header_lines, "scan_shape"))
        run_count = int(parse_header_value(header_lines, "run_count"))
        flattening_order = parse_header_value(header_lines, "flattening_order")
    else:
        raise ValueError("atom_numbers.txt is missing the tensor header")

    expected_size = int(np.prod(data_shape))
    if flat_values.size != expected_size:
        raise ValueError(
            f"atom_numbers.txt has {flat_values.size} values, expected {expected_size} from header"
        )

    tensor = flat_values.reshape(data_shape, order=flattening_order)
    if tensor.shape[0] != run_count:
        raise ValueError(
            f"Header run_count={run_count} does not match saved data shape {tensor.shape[0]}"
        )

    return tensor, scan_shape, run_count, flattening_order


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
        raise FileNotFoundError(f"No metadata*.json found in {images_directory.parent}")
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


def build_info_text(metadata: dict) -> str:
    """Build annotation text from scan settings."""
    scanned_variables = get_scanned_variables(metadata)
    scanned_variables_names = []
    for i in range(len(scanned_variables)):
        scanned_variables_names.append(scanned_variables[i]["name"])
    experiment_name = metadata["experimental_data"]["experiment_name"]

    is_multiple_runs = metadata.get("multiple_runs", 1)
    if is_multiple_runs:
        number_of_runs = int(metadata.get("number_of_runs", 1))
    else:
        number_of_runs = 1
    
    scan_info = scanned_variables[0]
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

    text_lines.append(f"N_runs = {number_of_runs}")

    if experiment_name == "MW_spectroscopy":

        if len(scanned_variables) == 1:
            Bx = metadata["sequence"][0]["analog"][0]["value"]
            By = metadata["sequence"][0]["analog"][1]["value"]
            Bz = metadata["sequence"][0]["analog"][2]["value"]
            text_lines.append(f"Bx = {Bx :.2f} V")
            text_lines.append(f"By = {By :.2f} V")
            text_lines.append(f"Bz = {Bz :.2f} V")

        if len(scanned_variables) == 2:
            if "Bx" in scanned_variables_names:
                By = metadata["sequence"][0]["analog"][1]["value"]
                Bz = metadata["sequence"][0]["analog"][2]["value"]
                text_lines.append(f"By = {By :.2f} V")
                text_lines.append(f"Bz = {Bz :.2f} V")
            if "By" in scanned_variables_names:
                Bx = metadata["sequence"][0]["analog"][0]["value"]
                Bz = metadata["sequence"][0]["analog"][2]["value"]
                text_lines.append(f"Bx = {Bx :.2f} V")
                text_lines.append(f"Bz = {Bz :.2f} V")
            if "Bz" in scanned_variables_names:
                Bx = metadata["sequence"][0]["analog"][0]["value"]
                By = metadata["sequence"][0]["analog"][1]["value"]
                text_lines.append(f"Bx = {Bx :.2f} V")
                text_lines.append(f"By = {By :.2f} V")

        if len(scanned_variables) == 3:
            if "Bx" not in scanned_variables_names:
                Bx = metadata["sequence"][0]["analog"][0]["value"]
                text_lines.append(f"Bx = {Bx :.2f} V")
            if "By" not in scanned_variables_names:
                By = metadata["sequence"][0]["analog"][1]["value"]
                text_lines.append(f"By = {By :.2f} V")
            if "Bz" not in scanned_variables_names:
                Bz = metadata["sequence"][0]["analog"][2]["value"]
                text_lines.append(f"Bz = {Bz :.2f} V")


    return "\n".join(text_lines)


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """Return the centered running average for a 1D array."""
    if window <= 0:
        raise ValueError("window must be positive")
    if values.ndim != 1:
        raise ValueError("moving_average only supports 1D arrays")
    if window > values.size:
        raise ValueError(f"moving_average window {window} is larger than the data length {values.size}")

    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(values, kernel, mode="valid")


def plot_1d_scan(
    ax,
    scan_axis: np.ndarray,
    atom_values: np.ndarray,
    atom_std: np.ndarray | None,
    x_label: str,
    info_text: str,
) -> None:
    atom_millions = atom_values * 1e-6
    if ENABLE_ERROR_BARS and atom_std is not None:
        atom_std_millions = atom_std * 1e-6
        ax.errorbar(
            scan_axis,
            atom_millions,
            yerr=atom_std_millions,
            fmt="-o",
            ms=3,
            lw=1,
            capsize=3,
            label="Data",
        )
    else:
        ax.plot(scan_axis, atom_millions, "-o", ms=3, lw=1, label="Data")

    if MOVING_AVERAGE_WINDOW > 0:
        averaged_axis = moving_average(scan_axis, MOVING_AVERAGE_WINDOW)
        averaged_values = moving_average(atom_millions, MOVING_AVERAGE_WINDOW)
        ax.plot(
            averaged_axis,
            averaged_values,
            "-",
            lw=2,
            label=f"Moving average (window={MOVING_AVERAGE_WINDOW})",
        )

    if ENABLE_SNR and ENABLE_ERROR_BARS and atom_std is not None:
        snr = np.divide(atom_values, atom_std, out=np.full_like(atom_values, np.nan, dtype=float), where=atom_std > 0)
        snr_axis = ax.twinx()
        snr_axis.plot(scan_axis, snr, "-s", ms=3, lw=1, color="tab:green", label="SNR")
        snr_axis.set_ylabel("SNR", color="tab:green")
        snr_axis.tick_params(axis="y", labelcolor="tab:green")
        snr_axis.grid(False)

        handles, labels = ax.get_legend_handles_labels()
        snr_handles, snr_labels = snr_axis.get_legend_handles_labels()
        ax.legend(handles + snr_handles, labels + snr_labels)
    else:
        ax.legend()

    ax.set_xlabel(x_label)
    ax.set_ylabel("Atom number (million)")
    ax.minorticks_on()
    ax.grid(True, which="both", alpha=0.35)

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def plot_2d_map(
    ax,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    atom_grid: np.ndarray,
    x_label: str,
    y_label: str,
    info_text: str,
) -> None:
    image = atom_grid.T * 1e-6
    extent = [float(x_axis[0]), float(x_axis[-1]), float(y_axis[0]), float(y_axis[-1])]
    mesh = ax.imshow(image, origin="lower", aspect="auto", extent=extent, interpolation="nearest")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.minorticks_on()
    ax.grid(False)
    plt.colorbar(mesh, ax=ax, label="Atom number (million)")

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def plot_3d_slider(
    fig,
    ax,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    z_axis: np.ndarray,
    atom_cube: np.ndarray,
    x_label: str,
    y_label: str,
    z_label: str,
    info_text: str,
) -> None:
    image = atom_cube[:, :, 0].T * 1e-6
    extent = [float(x_axis[0]), float(x_axis[-1]), float(y_axis[0]), float(y_axis[-1])]
    mesh = ax.imshow(image, origin="lower", aspect="auto", extent=extent, interpolation="nearest")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(f"{z_label} = {z_axis[0]:.6g}")
    plt.colorbar(mesh, ax=ax, label="Atom number (million)")

    slider_axis = fig.add_axes([0.18, 0.03, 0.64, 0.035])
    slider = Slider(
        ax=slider_axis,
        label=z_label,
        valmin=0,
        valmax=max(len(z_axis) - 1, 0),
        valinit=0,
        valstep=1,
    )

    def update(index_value: float) -> None:
        index = int(index_value)
        mesh.set_data(atom_cube[:, :, index].T * 1e-6)
        ax.set_title(f"{z_label} = {z_axis[index]:.6g}")
        fig.canvas.draw_idle()

    # Keep references so interactive widgets are not garbage-collected.
    fig._atom_slider = slider
    fig._atom_slider_axis = slider_axis
    slider.on_changed(update)

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def process_directory(directory: Path) -> None:
    directory = Path(directory)
    metadata_file = find_metadata_file(directory)

    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    scanned_variables = get_scanned_variables(metadata)
    scan_axes = build_scan_axes(scanned_variables)
    scan_info = scanned_variables[0]
    scan_label = metadata.get("experimental_data", {}).get("comment", "Scan value")
    info_text = build_info_text(metadata)
    axis_labels = [str(variable["name"]) for variable in scanned_variables]
    atom_tensor, scan_shape, run_count, _ = load_atom_number_tensor(directory / "atom_numbers.txt")

    if len(scanned_variables) != len(scan_shape):
        raise ValueError(
            f"Metadata scan dimensionality {len(scanned_variables)} does not match saved scan shape {scan_shape}"
        )

    atom_data = np.mean(atom_tensor, axis=0)
    atom_std = np.std(atom_tensor, axis=0, ddof=1) if run_count > 2 else None

    print(f"Plotting {directory}")
    print(f"Using metadata file: {metadata_file.name}")
    print(f"Averaging over {run_count} run(s)")

    if len(scanned_variables) == 1:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(14, 8), dpi=100)
        fig.suptitle(str(directory))
        maximize_figure_window(fig)
        plot_1d_scan(ax, scan_axes[0], atom_data, atom_std, scan_label, info_text)
    elif len(scanned_variables) == 2:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(14, 8), dpi=100)
        fig.suptitle(str(directory))
        maximize_figure_window(fig)
        plot_2d_map(ax, scan_axes[0], scan_axes[1], atom_data, axis_labels[0], axis_labels[1], info_text)
    elif len(scanned_variables) == 3:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(14, 8), dpi=100)
        fig.subplots_adjust(bottom=0.2)
        fig.suptitle(str(directory))
        maximize_figure_window(fig)
        plot_3d_slider(
            fig,
            ax,
            scan_axes[0],
            scan_axes[1],
            scan_axes[2],
            atom_data,
            axis_labels[0],
            axis_labels[1],
            axis_labels[2],
            info_text,
        )
    else:
        raise ValueError(f"Unsupported scan dimensionality: {len(scanned_variables)}")

    if len(scanned_variables) == 3:
        fig.tight_layout(rect=(0, 0.12, 1, 0.98))
    else:
        fig.tight_layout(rect=(0, 0, 1, 0.98))

    try:
        date_str = directory.parent.parent.name
        time_str = directory.parent.name
        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y_%m_%d_%H_%M_%S")
        data_timestamp = dt.strftime("%Y%m%d_%H%M%S")
    except Exception:
        data_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    
    output_path = directory.parents[2]/ "images" / f"atom_numbers_summary_{data_timestamp}.png"
    output_path.parent.mkdir(exist_ok=True)
    fig.savefig(output_path, dpi=150)
    print(f"Saved figure: {output_path}")


if __name__ == "__main__":
    main()
