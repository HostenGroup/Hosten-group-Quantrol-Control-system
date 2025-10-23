import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLabel

BASE_W, BASE_H = 1280, 720  # design baseline

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Explicit sizing")

        

        # create widgets
        self.label = QLabel("Adaptive text", self)
        self.label.setAlignment(Qt.AlignCenter)

        self.btn = QPushButton("Action", self)
        self._fit_to_work_area()
        self.apply_scale()

    def _fit_to_work_area(self):
        self.showNormal()
        QApplication.processEvents()
        screen = self.windowHandle().screen() or QGuiApplication.primaryScreen()
        work = screen.availableGeometry()
        frame = self.frameGeometry()
        client = self.geometry()
        ml = client.x() - frame.x()
        mt = client.y() - frame.y()
        mr = frame.right() - client.right()
        mb = frame.bottom() - client.bottom()
        self.setGeometry(work.adjusted(ml, mt, -mr, -mb))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.apply_scale()

    def apply_scale(self):
        w, h = self.width(), self.height()
        s = min(w / BASE_W, h / BASE_H)

        # scaled sizes
        label_w, label_h = int(400 * s), int(80 * s)
        btn_w, btn_h = int(200 * s), int(50 * s)

        # position elements manually
        self.label.setGeometry((w - label_w)//2, int(h * 0.3), label_w, label_h)
        self.btn.setGeometry((w - btn_w)//2, int(h * 0.6), btn_w, btn_h)

        # scale fonts
        self._set_font(self.label, 18 * s)
        self._set_font(self.btn,   12 * s)

    def _set_font(self, widget, pt):
        f = widget.font()
        f.setPointSizeF(max(8.0, pt))
        widget.setFont(f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Main()
    win.show()
    sys.exit(app.exec_())
