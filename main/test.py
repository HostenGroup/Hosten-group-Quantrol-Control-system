from PyQt5 import QtWidgets, QtCore

class GainExposureGroup(QtWidgets.QGroupBox):
    gainChanged = QtCore.pyqtSignal(str)
    exposureChanged = QtCore.pyqtSignal(str)
    exposureLockChanged = QtCore.pyqtSignal(bool)
    imageFormatChanged = QtCore.pyqtSignal(str)

    def __init__(self, title="Acquisition", parent=None):
        super().__init__(title, parent)
        self._build_ui()

    def _build_ui(self):
        form = QtWidgets.QFormLayout(self)

        # Gain, dB
        self.gain_edit = QtWidgets.QLineEdit(self)
        self.gain_edit.setPlaceholderText("e.g. 6.0")
        # self.gain_edit.textChanged.connect(self.gainChanged)
        form.addRow("Gain, dB", self.gain_edit)

        # Exposure time, ms + Lock
        exp_row = QtWidgets.QWidget(self)
        h = QtWidgets.QHBoxLayout(exp_row)
        h.setContentsMargins(0, 0, 0, 0)

        self.exposure_edit = QtWidgets.QLineEdit(exp_row)
        self.exposure_edit.setPlaceholderText("e.g. 500")
        # self.exposure_edit.textChanged.connect(self.exposureChanged)

        self.lock_cb = QtWidgets.QCheckBox("Lock", exp_row)
        self.lock_cb.toggled.connect(self._apply_lock)
        # self.lock_cb.toggled.connect(self.exposureLockChanged)

        h.addWidget(self.exposure_edit, 1)
        h.addWidget(self.lock_cb, 0)
        form.addRow("Exposure time, us", exp_row)

        # Image format
        self.format_combo = QtWidgets.QComboBox(self)
        self.format_combo.addItems(["Mono8", "Mono16"])
        # self.format_combo.currentTextChanged.connect(self.imageFormatChanged)
        form.addRow("Image format", self.format_combo)

    def _apply_lock(self, locked: bool):
        # Disable the field when locked (gives a clear visual cue in Qt5)
        self.exposure_edit.setEnabled(not locked)

    # Convenience
    def gain(self) -> str: return self.gain_edit.text()
    def setGain(self, v: str): self.gain_edit.setText(v)
    def exposureTimeMs(self) -> str: return self.exposure_edit.text()
    def setExposureTimeMs(self, v: str): self.exposure_edit.setText(v)
    def isExposureLocked(self) -> bool: return self.lock_cb.isChecked()
    def setExposureLocked(self, b: bool): self.lock_cb.setChecked(b)
    def imageFormat(self) -> str: return self.format_combo.currentText()
    def setImageFormat(self, t: str):
        i = self.format_combo.findText(t)
        if i >= 0: self.format_combo.setCurrentIndex(i)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(w)
    grp = GainExposureGroup()
    layout.addWidget(grp)
    layout.addStretch(1)
    w.setWindowTitle("Gain/Exposure Group Demo")
    w.resize(360, 160)
    w.show()
    sys.exit(app.exec_())  # PyQt5
