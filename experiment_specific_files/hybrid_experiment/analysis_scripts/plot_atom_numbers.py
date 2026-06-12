from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_DATA_ROOT = Path(r"G:\Experimental Data\Hybrid\MOT_images")
PATH_LIST_FILENAME = "path_list.txt"
ENABLE_PARABOLA_FIT = True


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


def get_experiment_root(directory: Path) -> Path:
    """Return the experiment root above date/time/image folders."""
    return directory.parents[2]


def parse_number_of_runs(metadata: dict) -> int:
    """Read Quantrol's multiple-runs count from metadata."""
    try:
        number_of_runs = int(metadata.get("number_of_runs", 1))
    except (TypeError, ValueError):
        number_of_runs = 1
    return max(number_of_runs, 1)


def average_multiple_runs(atom_numbers: np.ndarray, number_of_runs: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Average repeated scan blocks across runs and return scan, mean, and SEM."""
    if atom_numbers.ndim != 2 or atom_numbers.shape[1] < 2:
        raise ValueError("atom_numbers table must have at least two columns")

    total_rows = atom_numbers.shape[0]
    number_of_runs = max(int(number_of_runs), 1)
    usable_rows = (total_rows // number_of_runs) * number_of_runs
    if usable_rows <= 0:
        raise ValueError("Not enough rows to average over the requested number of runs")

    if usable_rows != total_rows:
        print(
            f"Warning: {total_rows} rows is not divisible by {number_of_runs}; "
            f"ignoring the last {total_rows - usable_rows} row(s)"
        )

    scan_points = usable_rows // number_of_runs
    if scan_points <= 0:
        raise ValueError("Averaging would produce zero scan points")

    atom_values = atom_numbers[:usable_rows, 0].reshape(number_of_runs, scan_points)
    scan_values = atom_numbers[:scan_points, 1].astype(float)
    mean_atom_numbers = np.mean(atom_values, axis=0)
    if number_of_runs > 1:
        sem_atom_numbers = np.std(atom_values, axis=0, ddof=1) / np.sqrt(number_of_runs)
    else:
        sem_atom_numbers = np.zeros_like(mean_atom_numbers)

    return scan_values, mean_atom_numbers, sem_atom_numbers


def fit_parabola(scan_values: np.ndarray, atom_values: np.ndarray) -> tuple[np.ndarray, float] | None:
    """Fit a quadratic curve to the plotted atom-number data."""
    valid = np.isfinite(scan_values) & np.isfinite(atom_values)
    x = np.asarray(scan_values[valid], dtype=float)
    y = np.asarray(atom_values[valid], dtype=float)
    if x.size < 3:
        return None
    if np.unique(x).size < 3:
        return None

    coeffs = np.polyfit(x, y, 2)
    y_fit = np.polyval(coeffs, x)
    ss_res = float(np.sum((y - y_fit) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return coeffs, r_squared


def plot_atom_number(
    ax,
    scan_label: str,
    atom_numbers: np.ndarray,
    info_text: str,
    number_of_runs: int,
) -> None:
    scan_values, mean_atom_numbers, sem_atom_numbers = average_multiple_runs(atom_numbers, number_of_runs)
    atom_millions = mean_atom_numbers * 1e-6
    sem_millions = sem_atom_numbers * 1e-6

    ax.errorbar(
        scan_values,
        atom_millions,
        yerr=sem_millions if number_of_runs > 1 else None,
        fmt="-o",
        ms=3,
        lw=1,
        capsize=2,
        label="Data",
    )

    if ENABLE_PARABOLA_FIT:
        fit_result = fit_parabola(scan_values, atom_millions)
        if fit_result is not None:
            coeffs, r_squared = fit_result
            dense_scan = np.linspace(float(np.min(scan_values)), float(np.max(scan_values)), 300)
            dense_fit = np.polyval(coeffs, dense_scan)
            fit_label = (
                f"Parabola fit: y={coeffs[0]:.4g}x^2 + {coeffs[1]:.4g}x + {coeffs[2]:.4g}"
            )
            if np.isfinite(r_squared):
                fit_label += f", R^2={r_squared:.4f}"
            ax.plot(dense_scan, dense_fit, "-", lw=2, label=fit_label)

    if scan_values.size > 1:
        scan_span = float(np.max(scan_values) - np.min(scan_values))
        if scan_span > 0:
            ax.set_xlim(np.min(scan_values) - 0.1 * scan_span, np.max(scan_values) + 0.1 * scan_span)
    ax.set_xlabel(scan_label)
    ax.set_ylabel("Atom number (million)")
    ax.minorticks_on()
    ax.grid(True, which="both", alpha=0.35)
    if number_of_runs > 1:
        ax.set_title(f"Averaged over {number_of_runs} runs")
    ax.legend()

    bbox = {"boxstyle": "round", "fc": "blanchedalmond", "ec": "orange", "alpha": 0.5}
    if info_text:
        ax.text(0.98, 0.05, info_text, bbox=bbox, transform=ax.transAxes, ha="right", va="bottom")


def process_directory(directory: Path) -> None:
    directory = Path(directory)
    metadata_file = find_metadata_file(directory)

    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    scan_info = metadata["scanned_variables"][0]
    scan_label = metadata.get("experimental_data", {}).get("comment", "Scan value")
    info_text = build_info_text(scan_info)
    number_of_runs = parse_number_of_runs(metadata)

    atom_numbers = load_required_table(directory / "atom_numbers.txt", expected_cols=2, table_name="atom_numbers")

    print(f"Plotting {directory}")
    print(f"Using metadata file: {metadata_file.name}")
    print(f"Averaging over {number_of_runs} run(s)")

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(14, 8), dpi=100)
    fig.suptitle(str(directory))
    maximize_figure_window(fig)

    plot_atom_number(ax, scan_label, atom_numbers, info_text, number_of_runs)

    fig.tight_layout(rect=(0, 0, 1, 0.98))

    try:
        date_str = directory.parent.parent.name
        time_str = directory.parent.name
        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y_%m_%d_%H_%M_%S")
        data_timestamp = dt.strftime("%Y%m%d_%H%M%S")
    except Exception:
        data_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = get_experiment_root(directory) / f"atom_numbers_summary_{data_timestamp}.png"
    fig.savefig(output_path, dpi=150)
    print(f"Saved figure: {output_path}")


def main() -> None:
    path_list_file = DEFAULT_DATA_ROOT / PATH_LIST_FILENAME
    target_directories = load_target_directories(path_list_file, take_last_n=1)

    for directory in target_directories:
        try:
            process_directory(directory)
        except KeyboardInterrupt:
            print("Stopped by user")
            break
        except Exception as exc:
            print(f"Skipping {directory}: {exc}")

    plt.show()


if __name__ == "__main__":
    main()
