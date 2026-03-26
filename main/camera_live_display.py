from __future__ import annotations

import argparse
import json
import signal
import socket
import struct
import sys
import time
from time import perf_counter

import numpy as np
import PySpin

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
        display_max_width: int,
        display_max_height: int,
        hardware_trigger: bool = False,
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
        self.display_max_width = max(int(display_max_width), 1)
        self.display_max_height = max(int(display_max_height), 1)
        self.hardware_trigger = bool(hardware_trigger)

        self._running = True
        self._subtract_enabled = bool(subtract_enabled)
        self._subtract_reference = None
        self._capture_reference_next = bool(subtract_enabled)
        self._control_socket = None

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
            if bool(payload.get("capture_reference_next", False)):
                self._capture_reference_next = True
            return

        if command == "reset_subtraction":
            self._subtract_reference = None
            self._capture_reference_next = True
            self._subtract_enabled = True
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

    @staticmethod
    def _to_display_uint8(arr: np.ndarray, subtraction_mode: bool = False) -> np.ndarray:
        if arr.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)

        if subtraction_mode:
            # For subtraction view, show magnitude of change regardless of sign.
            arr_abs = np.abs(arr)
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

    def _send_frame(self, sock_: socket.socket, frame8: np.ndarray, fps: float, get_ms: float, proc_ms: float) -> None:
        if frame8.ndim != 2:
            raise RuntimeError("Expected grayscale frame")
        height, width = frame8.shape
        payload = frame8.tobytes(order="C")
        header = struct.pack("!IIIfff", int(width), int(height), len(payload), float(fps), float(get_ms), float(proc_ms))
        sock_.sendall(header)
        sock_.sendall(payload)

    def _downsample_for_display(self, frame8: np.ndarray) -> np.ndarray:
        h, w = frame8.shape
        sx = max((w + self.display_max_width - 1) // self.display_max_width, 1)
        sy = max((h + self.display_max_height - 1) // self.display_max_height, 1)
        if sx == 1 and sy == 1:
            return frame8
        return frame8[::sy, ::sx]

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

        # Explicitly enforce automatic frame-rate mode for live view as requested.
        nodemap = cam.GetNodeMap()
        node_acq_fr_enable = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnable"))
        if PySpin.IsAvailable(node_acq_fr_enable) and PySpin.IsWritable(node_acq_fr_enable):
            node_acq_fr_enable.SetValue(False)
            print("Live: frame rate is set to automatic (AcquisitionFrameRateEnable=False)")
        else:
            print("Live: AcquisitionFrameRateEnable unavailable; keeping camera default behavior")

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
                t_get_end = perf_counter()

                try:
                    if image.IsIncomplete():
                        continue

                    t_proc_start = perf_counter()
                    arr = image.GetNDArray()
                    if arr.ndim == 3:
                        arr = arr[:, :, 0]

                    if self._subtract_enabled or self._capture_reference_next:
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
                        frame8 = self._to_display_uint8(frame_for_display, subtraction_mode=self._subtract_enabled)
                    else:
                        # Fast path when subtraction is disabled.
                        if arr.dtype == np.uint8:
                            frame8 = arr
                        elif arr.dtype == np.uint16:
                            frame8 = (arr >> 8).astype(np.uint8, copy=False)
                        else:
                            frame8 = self._to_display_uint8(arr.astype(np.float32, copy=False))

                    frame8 = self._downsample_for_display(frame8)
                    t_proc_end = perf_counter()

                    frame_counter += 1
                    elapsed = max(perf_counter() - t_start, 1e-9)
                    fps = frame_counter / elapsed
                    get_ms = (t_get_end - t_get_start) * 1000.0
                    proc_ms = (t_proc_end - t_proc_start) * 1000.0
                    self._send_frame(stream_sock, frame8, fps, get_ms, proc_ms)
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
    parser.add_argument("--display-max-width", type=int, default=1024, help="Maximum streamed frame width")
    parser.add_argument("--display-max-height", type=int, default=768, help="Maximum streamed frame height")
    parser.add_argument("--hardware-trigger", action="store_true", help="Use hardware trigger for live preview")
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
        display_max_width=args.display_max_width,
        display_max_height=args.display_max_height,
        hardware_trigger=args.hardware_trigger,
        subtract_enabled=args.subtract_enabled,
    )
    signal.signal(signal.SIGTERM, streamer.stop)
    signal.signal(signal.SIGINT, streamer.stop)
    return streamer.run()


if __name__ == "__main__":
    sys.exit(main())
