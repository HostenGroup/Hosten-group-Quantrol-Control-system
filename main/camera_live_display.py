from __future__ import annotations

import argparse
import importlib.util
import json
import signal
import socket
import struct
import sys
import time
from time import perf_counter
from pathlib import Path

import numpy as np
import PySpin
from scipy.ndimage import gaussian_filter

from camera import configure_camera, initialise_cameras


class LiveCameraStreamer:
    """Acquire frames with PySpin and stream display-ready grayscale frames over TCP."""

    def __init__(
        self,
        camera_name: str,
        pixel_format: str,
        gain_db: float,
        exposure_ms: float,
        stream_host: str,
        stream_port: int,
        control_host: str,
        control_port: int,
        downsample_factor: float,
        target_fps: float,
        hardware_trigger: bool = False,
        gaussian_enabled: bool = False,
        gaussian_sigma: float = 1.0,
        gaussian_kernel: int = 5,
        display_gain: float = 0.0,
        dynamic_subtraction_enabled: bool = False,
        sequence_trigger_count: int = 0,
        fps_limit_enabled: bool = False,
        subtract_enabled: bool = False,
    ) -> None:
        self.camera_name = camera_name
        self.pixel_format = pixel_format
        self.gain_db = gain_db
        self.exposure_ms = exposure_ms
        self.stream_host = stream_host
        self.stream_port = int(stream_port)
        self.control_host = control_host
        self.control_port = int(control_port)
        self.downsample_factor = float(downsample_factor)
        if self.downsample_factor <= 0.0:
            self.downsample_factor = 1.0
        self.target_fps = float(target_fps)
        if self.target_fps <= 0.0:
            self.target_fps = 1.0
        self.hardware_trigger = bool(hardware_trigger)
        self.gaussian_enabled = bool(gaussian_enabled)
        self.gaussian_sigma = float(gaussian_sigma) if float(gaussian_sigma) > 0 else 1.0
        self.gaussian_kernel = int(gaussian_kernel)
        if self.gaussian_kernel < 1:
            self.gaussian_kernel = 1
        if self.gaussian_kernel % 2 == 0:
            self.gaussian_kernel += 1
        self.display_gain = float(display_gain)
        self.dynamic_subtraction_enabled = bool(dynamic_subtraction_enabled)
        self.sequence_trigger_count = int(sequence_trigger_count)
        if self.sequence_trigger_count < 0:
            self.sequence_trigger_count = 0
        self.fps_limit_enabled = bool(fps_limit_enabled)

        self._running = True
        self._subtract_enabled = bool(subtract_enabled)
        self._subtract_reference = None
        self._capture_reference_next = bool(subtract_enabled)
        self._dynamic_frame_index = 0
        self._control_socket = None
        self._atom_count_func = self._load_atom_count_function()

    def _load_atom_count_function(self):
        """Load atom_count() from experiment_specific_files/hybrid_experiment/atom_count.py."""
        try:
            atom_count_path = Path(__file__).resolve().parent.parent / "experiment_specific_files" / "hybrid_experiment" / "atom_count.py"
            if not atom_count_path.exists():
                return None

            spec = importlib.util.spec_from_file_location("quantrol_live_atom_count", str(atom_count_path))
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            fn = getattr(module, "atom_count", None)
            return fn if callable(fn) else None
        except Exception as exc:
            print(f"Live atom count loader failed: {exc}")
            return None

    def _compute_atom_count(self, arr_for_count: np.ndarray, pixel_format_for_count: str) -> float:
        """Compute atom count from the same processed frame shown to the user (before downsampling)."""
        if self._atom_count_func is None or arr_for_count is None or arr_for_count.size == 0:
            return float("nan")

        try:
            camera_counts_number = float(np.sum(arr_for_count, dtype=np.float64))
            total_gain_db = float(self.gain_db) + float(self.display_gain)
            t_exp_s = max(float(self.exposure_ms) * 1e-3, 1e-9)
            pixel_format = str(pixel_format_for_count)
            value = self._atom_count_func(camera_counts_number, total_gain_db, t_exp_s, pixel_format)
            return float(value)
        except Exception:
            return float("nan")

    def stop(self, *_args) -> None:
        self._running = False
        if self._control_socket is not None:
            try:
                self._control_socket.close()
            except Exception:
                pass

    def _connect_stream_socket(self) -> socket.socket:
        sock_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        deadline = time.time() + 5.0
        last_exc = None
        while time.time() < deadline and self._running:
            try:
                sock_.connect((self.stream_host, self.stream_port))
                sock_.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                return sock_
            except OSError as exc:
                last_exc = exc
                time.sleep(0.1)
        sock_.close()
        if last_exc is not None:
            raise RuntimeError(f"Could not connect to Quantrol live stream socket: {last_exc}")
        raise RuntimeError("Could not connect to Quantrol live stream socket")

    def _create_control_socket(self) -> socket.socket:
        sock_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_.bind((self.control_host, self.control_port))
        sock_.setblocking(False)
        return sock_

    def _poll_control_commands(self, cam: PySpin.Camera) -> None:
        if self._control_socket is None:
            return
        while self._running:
            try:
                packet, _addr = self._control_socket.recvfrom(4096)
            except BlockingIOError:
                break
            except OSError:
                break

            try:
                payload = json.loads(packet.decode("utf-8"))
            except Exception:
                continue
            self._apply_control_command(cam, payload)

    def _apply_control_command(self, cam: PySpin.Camera, payload: dict) -> None:
        command = str(payload.get("cmd", "")).strip().lower()
        if command == "set_subtraction":
            self._subtract_enabled = bool(payload.get("enabled", False))
            if not self._subtract_enabled:
                self._dynamic_frame_index = 0
            if bool(payload.get("capture_reference_next", False)):
                self._capture_reference_next = True
            return

        if command == "reset_subtraction":
            self._subtract_reference = None
            self._capture_reference_next = True
            self._subtract_enabled = True
            self._dynamic_frame_index = 0
            return

        if command == "reset_dynamic_subtraction_counter":
            self._dynamic_frame_index = 0
            self._subtract_reference = None
            return

        if command == "apply_params":
            try:
                if "gain_db" in payload:
                    self.gain_db = float(payload.get("gain_db"))
                if "exposure_ms" in payload:
                    self.exposure_ms = float(payload.get("exposure_ms"))
                if "pixel_format" in payload:
                    self.pixel_format = str(payload.get("pixel_format") or self.pixel_format)
                if "hardware_trigger" in payload:
                    self.hardware_trigger = bool(payload.get("hardware_trigger"))
                if "dynamic_subtraction_enabled" in payload:
                    self.dynamic_subtraction_enabled = bool(payload.get("dynamic_subtraction_enabled"))
                    self._dynamic_frame_index = 0
                    if self.dynamic_subtraction_enabled:
                        self._subtract_reference = None
                if "sequence_trigger_count" in payload:
                    count_value = int(payload.get("sequence_trigger_count"))
                    self.sequence_trigger_count = count_value if count_value >= 0 else 0
                    self._dynamic_frame_index = 0
                    if self.dynamic_subtraction_enabled:
                        self._subtract_reference = None
                if "gaussian_enabled" in payload:
                    self.gaussian_enabled = bool(payload.get("gaussian_enabled"))
                if "gaussian_sigma" in payload:
                    sigma_value = float(payload.get("gaussian_sigma"))
                    self.gaussian_sigma = sigma_value if sigma_value > 0 else 1.0
                if "gaussian_kernel" in payload:
                    kernel_value = int(float(payload.get("gaussian_kernel")))
                    if kernel_value < 1:
                        kernel_value = 1
                    if kernel_value % 2 == 0:
                        kernel_value += 1
                    self.gaussian_kernel = kernel_value
                if "display_gain" in payload:
                    gain_value = float(payload.get("display_gain"))
                    self.display_gain = gain_value
                if "downsample_factor" in payload:
                    factor_value = float(payload.get("downsample_factor"))
                    self.downsample_factor = factor_value if factor_value > 0.0 else 1.0
                if "fps_limit_enabled" in payload:
                    self.fps_limit_enabled = bool(payload.get("fps_limit_enabled"))
                if "target_fps" in payload:
                    fps_value = float(payload.get("target_fps"))
                    self.target_fps = fps_value if fps_value > 0.0 else 1.0

                was_acquiring = False
                try:
                    cam.EndAcquisition()
                    was_acquiring = True
                except Exception:
                    pass

                self._configure_camera_for_live(cam)

                if was_acquiring:
                    cam.BeginAcquisition()
            except Exception as exc:
                print(f"Live apply_params failed: {exc}")
            return

    def _apply_gaussian_if_enabled(self, arr: np.ndarray) -> np.ndarray:
        if not self.gaussian_enabled:
            return arr

        # Keep the same intensity scale/type so enabling Gaussian does not auto-brighten.
        arrf = arr.astype(np.float32, copy=False)
        sigma = max(float(self.gaussian_sigma), 1e-6)
        radius = max((int(self.gaussian_kernel) - 1) / 2.0, 0.0)
        truncate = max(radius / sigma, 0.01)
        filtered = gaussian_filter(arrf, sigma=sigma, mode="nearest", truncate=truncate)

        if arr.dtype == np.uint8:
            return np.clip(np.rint(filtered), 0.0, 255.0).astype(np.uint8)
        if arr.dtype == np.uint16:
            return np.clip(np.rint(filtered), 0.0, 65535.0).astype(np.uint16)
        return filtered

    def _apply_display_gain(self, arr: np.ndarray) -> np.ndarray:
        # Interpret display gain in camera-style dB (amplitude): +20 dB -> 10x.
        gain = float(10.0 ** (float(self.display_gain) / 20.0))
        if abs(gain - 1.0) < 1e-9:
            return arr

        if np.issubdtype(arr.dtype, np.floating):
            return arr * gain

        arrf = arr.astype(np.float32, copy=False) * gain
        if arr.dtype == np.uint8:
            return np.clip(np.rint(arrf), 0.0, 255.0).astype(np.uint8)
        if arr.dtype == np.uint16:
            return np.clip(np.rint(arrf), 0.0, 65535.0).astype(np.uint16)
        return arrf

    @staticmethod
    def _to_display_uint8(
        arr: np.ndarray,
        subtraction_mode: bool = False,
        subtraction_full_scale: float | None = None,
    ) -> np.ndarray:
        if arr.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)

        if subtraction_mode:
            # For subtraction view, show magnitude of change regardless of sign.
            arr_abs = np.abs(arr)
            if subtraction_full_scale is not None and subtraction_full_scale > 0.0:
                max_abs = float(subtraction_full_scale)
            else:
                max_abs = float(np.max(arr_abs))
            if max_abs <= 0.0:
                return np.zeros(arr.shape, dtype=np.uint8)
            scaled = arr_abs * (255.0 / max_abs)
            return np.clip(scaled, 0.0, 255.0).astype(np.uint8)

        arr_min = float(np.min(arr))
        arr_max = float(np.max(arr))
        if arr_min == arr_max:
            return np.zeros(arr.shape, dtype=np.uint8)

        if arr_min < 0.0:
            max_abs = max(abs(arr_min), abs(arr_max), 1e-9)
            scaled = (arr + max_abs) * (255.0 / (2.0 * max_abs))
        else:
            scaled = (arr - arr_min) * (255.0 / (arr_max - arr_min))

        return np.clip(scaled, 0.0, 255.0).astype(np.uint8)

    def _send_frame(
        self,
        sock_: socket.socket,
        frame8: np.ndarray,
        fps: float,
        get_ms: float,
        proc_ms: float,
        atom_count: float,
    ) -> None:
        if frame8.ndim != 2:
            raise RuntimeError("Expected grayscale frame")
        height, width = frame8.shape
        payload = frame8.tobytes(order="C")
        header = struct.pack("!IIIffff", int(width), int(height), len(payload), float(fps), float(get_ms), float(proc_ms), float(atom_count))
        sock_.sendall(header)
        sock_.sendall(payload)

    def _downsample_for_display(self, frame8: np.ndarray) -> np.ndarray:
        factor = float(self.downsample_factor)
        if factor <= 1.0:
            return frame8

        h, w = frame8.shape
        out_w = max(int(round(w / factor)), 1)
        out_h = max(int(round(h / factor)), 1)
        if out_w >= w and out_h >= h:
            return frame8

        x_idx = np.clip((np.arange(out_w, dtype=np.float32) * factor).astype(np.int32), 0, w - 1)
        y_idx = np.clip((np.arange(out_h, dtype=np.float32) * factor).astype(np.int32), 0, h - 1)
        return frame8[np.ix_(y_idx, x_idx)]

    def _configure_camera_for_live(self, cam: PySpin.Camera) -> None:
        """Apply the same baseline configuration used by camera.py plus live-specific safety checks."""
        info = {}
        configure_camera(
            cam=cam,
            exposure_us=max(self.exposure_ms, 0.0) * 1000.0,
            gain_db=self.gain_db,
            format_name=self.pixel_format,
            info=info,
        )

        # Configure frame rate mode for live view.
        nodemap = cam.GetNodeMap()
        node_acq_fr_enable = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnable"))
        node_acq_fr = PySpin.CFloatPtr(nodemap.GetNode("AcquisitionFrameRate"))
        if PySpin.IsAvailable(node_acq_fr_enable) and PySpin.IsWritable(node_acq_fr_enable):
            node_acq_fr_enable.SetValue(bool(self.fps_limit_enabled))
            if self.fps_limit_enabled and PySpin.IsAvailable(node_acq_fr) and PySpin.IsWritable(node_acq_fr):
                req_fps = max(float(self.target_fps), 1.0)
                req_fps = max(min(req_fps, node_acq_fr.GetMax()), node_acq_fr.GetMin())
                node_acq_fr.SetValue(req_fps)
                print(f"Live: frame rate limit enabled at {req_fps:.3f} FPS")
            elif self.fps_limit_enabled:
                print("Live: FPS limit requested but AcquisitionFrameRate node is unavailable")
            else:
                print("Live: frame rate is set to automatic (AcquisitionFrameRateEnable=False)")
        else:
            print("Live: AcquisitionFrameRateEnable unavailable; keeping camera default behavior")

        # Force low-latency stream buffering for preview. NewestOnly avoids a fixed stale-frame offset.
        try:
            tl_stream = cam.GetTLStreamNodeMap()

            node_handling = PySpin.CEnumerationPtr(tl_stream.GetNode("StreamBufferHandlingMode"))
            if PySpin.IsAvailable(node_handling) and PySpin.IsWritable(node_handling):
                newest = node_handling.GetEntryByName("NewestOnly")
                if PySpin.IsAvailable(newest) and PySpin.IsReadable(newest):
                    node_handling.SetIntValue(newest.GetValue())
                    print("Live: StreamBufferHandlingMode set to NewestOnly")
                else:
                    print("Live: NewestOnly stream buffer mode unavailable; keeping camera default")
            else:
                print("Live: StreamBufferHandlingMode node unavailable; keeping camera default")

            node_count_mode = PySpin.CEnumerationPtr(tl_stream.GetNode("StreamBufferCountMode"))
            if PySpin.IsAvailable(node_count_mode) and PySpin.IsWritable(node_count_mode):
                manual = node_count_mode.GetEntryByName("Manual")
                if PySpin.IsAvailable(manual) and PySpin.IsReadable(manual):
                    node_count_mode.SetIntValue(manual.GetValue())

            node_count_manual = PySpin.CIntegerPtr(tl_stream.GetNode("StreamBufferCountManual"))
            if PySpin.IsAvailable(node_count_manual) and PySpin.IsWritable(node_count_manual):
                target_count = int(node_count_manual.GetMin())
                target_count = max(min(target_count, node_count_manual.GetMax()), node_count_manual.GetMin())
                node_count_manual.SetValue(target_count)
                print(f"Live: StreamBufferCountManual set to {target_count}")
        except Exception as exc:
            print(f"Live: could not apply low-latency stream buffer settings: {exc}")

        # Live preview defaults to free-running. Optionally keep hardware trigger when requested.
        trig_mode = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerMode"))
        if PySpin.IsAvailable(trig_mode) and PySpin.IsWritable(trig_mode):
            mode_name = "On" if self.hardware_trigger else "Off"
            trig_mode_entry = trig_mode.GetEntryByName(mode_name)
            if PySpin.IsAvailable(trig_mode_entry) and PySpin.IsReadable(trig_mode_entry):
                trig_mode.SetIntValue(trig_mode_entry.GetValue())
                if self.hardware_trigger:
                    print("Live: TriggerMode set to On (hardware trigger preview)")
                else:
                    print("Live: TriggerMode set to Off (free-running preview)")
            else:
                print(f"Live: TriggerMode {mode_name} entry unavailable; keeping existing trigger mode")
        else:
            print("Live: TriggerMode node unavailable; keeping existing trigger mode")

    def run(self) -> int:
        system = None
        cam_list = None
        cam = None
        stream_sock = None
        control_sock = None
        frame_counter = 0
        t_start = perf_counter()

        try:
            import config

            if self.camera_name not in config.camera_serial_numbers_dict:
                raise ValueError(f"Camera label '{self.camera_name}' is not configured")

            stream_sock = self._connect_stream_socket()
            print(f"Connected to Quantrol stream at {self.stream_host}:{self.stream_port}")
            control_sock = self._create_control_socket()
            self._control_socket = control_sock
            print(f"Live control listener on {self.control_host}:{self.control_port}")

            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            if cam_list.GetSize() == 0:
                raise RuntimeError("No FLIR cameras detected.")

            camera_dict = initialise_cameras(cam_list)
            if self.camera_name not in camera_dict:
                raise RuntimeError(f"Requested camera '{self.camera_name}' not detected.")

            cam = camera_dict[self.camera_name]
            self._configure_camera_for_live(cam)

            cam.BeginAcquisition()
            print("Live camera acquisition started")

            while self._running:
                self._poll_control_commands(cam)
                t_get_start = perf_counter()
                try:
                    image = cam.GetNextImage(100)
                except PySpin.SpinnakerException as exc:
                    if "[-1011]" in str(exc):
                        continue
                    raise

                # Drain any queued frames and keep only the newest one.
                # This removes fixed latency when camera/driver buffering persists.
                while self._running:
                    try:
                        newer_image = cam.GetNextImage(0)
                    except PySpin.SpinnakerException as exc:
                        if "[-1011]" in str(exc):
                            break
                        raise

                    try:
                        image.Release()
                    except Exception:
                        pass
                    image = newer_image

                t_get_end = perf_counter()

                try:
                    if image.IsIncomplete():
                        continue

                    t_proc_start = perf_counter()
                    arr = image.GetNDArray()
                    if arr.ndim == 3:
                        arr = arr[:, :, 0]
                    subtraction_full_scale = None
                    if arr.dtype == np.uint8:
                        subtraction_full_scale = 255.0
                    elif arr.dtype == np.uint16:
                        subtraction_full_scale = 65535.0
                    arr = self._apply_gaussian_if_enabled(arr)

                    if self.dynamic_subtraction_enabled and self._subtract_enabled:
                        cycle_count = int(self.sequence_trigger_count)
                        if cycle_count < 2:
                            cycle_count = 2
                        arrf = arr.astype(np.float32, copy=False)
                        cycle_pos = self._dynamic_frame_index % cycle_count
                        if cycle_pos == 0 or self._subtract_reference is None:
                            self._subtract_reference = arrf.copy()
                            self._dynamic_frame_index = (self._dynamic_frame_index + 1) % cycle_count
                            # First trigger in each cycle is the dynamic background; do not display it.
                            continue

                        frame_for_display = arrf - self._subtract_reference
                        self._dynamic_frame_index = (self._dynamic_frame_index + 1) % cycle_count
                        frame_for_display = self._apply_display_gain(frame_for_display)
                        frame8 = self._to_display_uint8(
                            frame_for_display,
                            subtraction_mode=True,
                            subtraction_full_scale=subtraction_full_scale,
                        )
                    elif self._subtract_enabled or self._capture_reference_next:
                        arrf = arr.astype(np.float32, copy=False)
                        if self._capture_reference_next:
                            self._subtract_reference = arrf.copy()
                            self._capture_reference_next = False
                            print("Subtraction reference captured")
                            frame_for_display = arrf
                        elif self._subtract_reference is not None:
                            if self._subtract_reference.shape == arrf.shape:
                                frame_for_display = arrf - self._subtract_reference
                            else:
                                frame_for_display = arrf
                                print("Subtraction skipped due to shape mismatch")
                        else:
                            frame_for_display = arrf
                        frame_for_display = self._apply_display_gain(frame_for_display)
                        frame8 = self._to_display_uint8(
                            frame_for_display,
                            subtraction_mode=self._subtract_enabled,
                            subtraction_full_scale=subtraction_full_scale,
                        )
                    else:
                        # Fast path when subtraction is disabled.
                        arr = self._apply_display_gain(arr)
                        if arr.dtype == np.uint8:
                            frame8 = arr
                        elif arr.dtype == np.uint16:
                            frame8 = (arr >> 8).astype(np.uint8, copy=False)
                        else:
                            frame8 = self._to_display_uint8(arr.astype(np.float32, copy=False))

                    # Atom count follows the displayed processing chain, but excludes display downsampling.
                    atom_count_value = self._compute_atom_count(frame8, "Mono8")
                    frame8 = self._downsample_for_display(frame8)
                    t_proc_end = perf_counter()

                    frame_counter += 1
                    elapsed = max(perf_counter() - t_start, 1e-9)
                    fps = frame_counter / elapsed
                    get_ms = (t_get_end - t_get_start) * 1000.0
                    proc_ms = (t_proc_end - t_proc_start) * 1000.0
                    self._send_frame(stream_sock, frame8, fps, get_ms, proc_ms, atom_count_value)
                finally:
                    image.Release()

            print("Live camera acquisition stopped")
            return 0

        except Exception as exc:
            print(f"Live camera error: {exc}")
            return 1
        finally:
            if cam is not None:
                try:
                    cam.EndAcquisition()
                except Exception:
                    pass

            if cam_list is not None:
                for cam_obj in cam_list:
                    try:
                        cam_obj.DeInit()
                    except Exception:
                        pass
                cam_list.Clear()

            if system is not None:
                try:
                    system.ReleaseInstance()
                except Exception:
                    pass

            if stream_sock is not None:
                try:
                    stream_sock.close()
                except Exception:
                    pass

            if control_sock is not None:
                try:
                    control_sock.close()
                except Exception:
                    pass
            self._control_socket = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live FLIR camera acquisition streamer")
    parser.add_argument("--camera", required=True, help="Camera label as defined in config.camera_serial_numbers_dict")
    parser.add_argument("--format", required=True, help="Pixel format name, e.g. Mono8")
    parser.add_argument("--gain-db", required=True, type=float, help="Analog gain in dB")
    parser.add_argument("--exposure-ms", required=True, type=float, help="Exposure time in milliseconds")
    parser.add_argument("--stream-host", required=True, help="Quantrol host for frame stream")
    parser.add_argument("--stream-port", required=True, type=int, help="Quantrol TCP port for frame stream")
    parser.add_argument("--control-host", required=True, help="Quantrol host for control commands")
    parser.add_argument("--control-port", required=True, type=int, help="Quantrol UDP port for control commands")
    parser.add_argument("--downsample-factor", type=float, default=2.0, help="Uniform display downsampling factor (float > 0)")
    parser.add_argument("--target-fps", type=float, default=12.0, help="Target camera FPS when FPS limit is enabled")
    parser.add_argument("--display-gain", type=float, default=0.0, help="Display-only digital gain in camera-style dB (20 dB = 10x)")
    parser.add_argument("--dynamic-subtraction-enabled", dest="dynamic_subtraction_enabled", action="store_true", help="Enable dynamic background subtraction mode")
    parser.add_argument("--dynamic-subtraction-disabled", dest="dynamic_subtraction_enabled", action="store_false", help="Disable dynamic background subtraction mode")
    parser.set_defaults(dynamic_subtraction_enabled=False)
    parser.add_argument("--sequence-trigger-count", type=int, default=0, help="Number of camera trigger events in one sequence cycle")
    parser.add_argument("--fps-limit-enabled", dest="fps_limit_enabled", action="store_true", help="Enable camera FPS limiting")
    parser.add_argument("--fps-limit-disabled", dest="fps_limit_enabled", action="store_false", help="Disable camera FPS limiting")
    parser.set_defaults(fps_limit_enabled=False)
    parser.add_argument("--hardware-trigger", action="store_true", help="Use hardware trigger for live preview")
    parser.add_argument("--gaussian-enabled", action="store_true", help="Enable gaussian filtering")
    parser.add_argument("--gaussian-sigma", type=float, default=1.0, help="Gaussian sigma in pixels")
    parser.add_argument("--gaussian-kernel", type=int, default=5, help="Gaussian kernel size (odd integer)")
    parser.add_argument("--subtract-enabled", action="store_true", help="Enable subtraction at startup")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    streamer = LiveCameraStreamer(
        camera_name=args.camera,
        pixel_format=args.format,
        gain_db=args.gain_db,
        exposure_ms=args.exposure_ms,
        stream_host=args.stream_host,
        stream_port=args.stream_port,
        control_host=args.control_host,
        control_port=args.control_port,
        downsample_factor=args.downsample_factor,
        target_fps=args.target_fps,
        hardware_trigger=args.hardware_trigger,
        gaussian_enabled=args.gaussian_enabled,
        gaussian_sigma=args.gaussian_sigma,
        gaussian_kernel=args.gaussian_kernel,
        display_gain=args.display_gain,
        dynamic_subtraction_enabled=args.dynamic_subtraction_enabled,
        sequence_trigger_count=args.sequence_trigger_count,
        fps_limit_enabled=args.fps_limit_enabled,
        subtract_enabled=args.subtract_enabled,
    )
    signal.signal(signal.SIGTERM, streamer.stop)
    signal.signal(signal.SIGINT, streamer.stop)
    return streamer.run()


if __name__ == "__main__":
    sys.exit(main())
