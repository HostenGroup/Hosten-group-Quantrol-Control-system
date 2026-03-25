from __future__ import annotations

import argparse
import sys
from time import perf_counter
from typing import Optional

import numpy as np
import PySpin
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from camera import configure_camera, initialise_cameras


class CameraWorker(QObject):
    frame_ready = pyqtSignal(object, float)
    status_ready = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, camera_name: str, pixel_format: str, gain_db: float, exposure_ms: float) -> None:
        super().__init__()
        self.camera_name = camera_name
        self.pixel_format = pixel_format
        self.gain_db = gain_db
        self.exposure_ms = exposure_ms

        self._running = False
        self._subtract_enabled = False
        self._subtract_reference: Optional[np.ndarray] = None
        self._capture_reference_next = False

    @pyqtSlot()
    def run(self) -> None:
        self._running = True
        system = None
        cam_list = None
        cam = None

        frame_counter = 0
        t_start = perf_counter()

        try:
            import config

            serial_numbers = config.camera_serial_numbers_dict
            if self.camera_name not in serial_numbers:
                raise ValueError(f"Camera label '{self.camera_name}' is not configured")

            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            if cam_list.GetSize() == 0:
                raise RuntimeError("No FLIR cameras detected.")

            camera_dict = initialise_cameras(cam_list)
            if self.camera_name not in camera_dict:
                raise RuntimeError(f"Requested camera '{self.camera_name}' not detected.")

            cam = camera_dict[self.camera_name]
            info = {}
            configure_camera(
                cam=cam,
                exposure_us=max(self.exposure_ms, 0.0) * 1000.0,
                gain_db=self.gain_db,
                format_name=self.pixel_format,
                info=info,
            )

            cam.BeginAcquisition()
            self.status_ready.emit("Live camera acquisition started")

            while self._running:
                try:
                    image = cam.GetNextImage(100)
                except PySpin.SpinnakerException as exc:
                    if "[-1011]" in str(exc):
                        continue
                    raise

                try:
                    if image.IsIncomplete():
                        continue

                    arr = image.GetNDArray()
                    if arr.ndim == 3:
                        arr = arr[:, :, 0]
                    arr = arr.astype(np.float32, copy=False)

                    if self._capture_reference_next:
                        self._subtract_reference = arr.copy()
                        self._capture_reference_next = False
                        self.status_ready.emit("Subtraction reference captured from next acquired frame")
                        frame_for_display = arr
                    elif self._subtract_enabled and self._subtract_reference is not None:
                        if self._subtract_reference.shape == arr.shape:
                            frame_for_display = arr - self._subtract_reference
                        else:
                            frame_for_display = arr
                            self.status_ready.emit("Subtraction skipped due to shape mismatch")
                    else:
                        frame_for_display = arr

                    frame8 = self._to_display_uint8(frame_for_display)
                    frame_counter += 1
                    elapsed = max(perf_counter() - t_start, 1e-9)
                    fps = frame_counter / elapsed
                    self.frame_ready.emit(frame8, fps)
                finally:
                    image.Release()

        except Exception as exc:
            self.error.emit(str(exc))
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

            self.status_ready.emit("Live camera acquisition stopped")
            self.finished.emit()

    @pyqtSlot()
    def stop(self) -> None:
        self._running = False

    @pyqtSlot(bool)
    def set_subtraction_enabled(self, enabled: bool) -> None:
        self._subtract_enabled = bool(enabled)

    @pyqtSlot()
    def arm_next_reference_capture(self) -> None:
        self._capture_reference_next = True

    @pyqtSlot()
    def clear_reference(self) -> None:
        self._subtract_reference = None
        self._capture_reference_next = False

    @staticmethod
    def _to_display_uint8(arr: np.ndarray) -> np.ndarray:
        if arr.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)

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


class LiveCameraWindow(QMainWindow):
    def __init__(
        self,
        camera_name: str,
        pixel_format: str,
        gain_db: float,
        exposure_ms: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Live camera view: {camera_name}")
        self.resize(920, 700)

        self.image_label = QLabel("Waiting for frames...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("background-color: black; color: white;")

        self.status_label = QLabel("Idle")

        root_layout = QVBoxLayout()
        root_layout.addWidget(self.image_label)
        root_layout.addWidget(self.status_label)

        root = QWidget()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self.thread = QThread(self)
        self.worker = CameraWorker(
            camera_name=camera_name,
            pixel_format=pixel_format,
            gain_db=gain_db,
            exposure_ms=exposure_ms,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.status_ready.connect(self._on_status)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_worker_finished)

        self.start_stream()

    def start_stream(self) -> None:
        if not self.thread.isRunning():
            self.thread.start()

    def stop_stream(self) -> None:
        self.worker.stop()
        self.thread.quit()
        self.thread.wait(2500)

    def set_subtraction_enabled(self, enabled: bool) -> None:
        self.worker.set_subtraction_enabled(bool(enabled))

    def arm_next_subtraction_reference(self) -> None:
        self.worker.arm_next_reference_capture()

    def reset_subtraction_reference(self) -> None:
        self.worker.arm_next_reference_capture()

    def clear_subtraction_reference(self) -> None:
        self.worker.clear_reference()

    @pyqtSlot(object, float)
    def _on_frame_ready(self, frame8: object, fps: float) -> None:
        array = np.asarray(frame8)
        h, w = array.shape
        image = QImage(array.data, w, h, array.strides[0], QImage.Format_Grayscale8).copy()
        pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(
            pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        )
        self.status_label.setText(f"Streaming | FPS: {fps:.1f} | Size: {w}x{h}")

    @pyqtSlot(str)
    def _on_status(self, text: str) -> None:
        self.status_label.setText(text)

    @pyqtSlot(str)
    def _on_error(self, text: str) -> None:
        self.status_label.setText(f"Error: {text}")

    @pyqtSlot()
    def _on_worker_finished(self) -> None:
        pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.stop_stream()
        super().closeEvent(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live FLIR camera display")
    parser.add_argument("--camera", required=True, help="Camera label as defined in config.camera_serial_numbers_dict")
    parser.add_argument("--format", required=True, help="Pixel format name, e.g. Mono8")
    parser.add_argument("--gain-db", required=True, type=float, help="Analog gain in dB")
    parser.add_argument("--exposure-ms", required=True, type=float, help="Exposure time in milliseconds")
    parser.add_argument("--subtract-enabled", action="store_true", help="Enable subtraction at startup")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    window = LiveCameraWindow(
        camera_name=args.camera,
        pixel_format=args.format,
        gain_db=args.gain_db,
        exposure_ms=args.exposure_ms,
    )
    if args.subtract_enabled:
        window.set_subtraction_enabled(True)
        window.arm_next_subtraction_reference()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
