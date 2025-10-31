# PyQt5==5.15.4
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QListWidget, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt


class Picker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("List picker")

        # Top: chosen element line
        self.chosen_label = QLabel("Chosen element")
        self.chosen_line = QLineEdit()
        self.chosen_line.setReadOnly(True)

        top_box = QVBoxLayout()
        top_box.addWidget(self.chosen_label)
        top_box.addWidget(self.chosen_line)

        # Center: list of items
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_chosen)

        # Bottom: add-new line and buttons
        self.new_label = QLabel("Add new element")
        self.new_line = QLineEdit()
        self.new_line.setPlaceholderText("Type new element and press Enter or click Add")
        self.new_line.returnPressed.connect(self.add_element)

        self.btn_add = QPushButton("Add new element")
        self.btn_add.clicked.connect(self.add_element)

        self.btn_delete = QPushButton("Delete element")
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_delete.setEnabled(False)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.new_line, 1)
        bottom_row.addWidget(self.btn_add)
        bottom_row.addWidget(self.btn_delete)

        bottom_box = QVBoxLayout()
        bottom_box.addWidget(self.new_label)
        bottom_box.addLayout(bottom_row)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addLayout(top_box)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(bottom_box)

        # Demo data
        for name in ["Alpha", "Beta", "Gamma"]:
            self.list_widget.addItem(name)

        self.list_widget.itemSelectionChanged.connect(self._toggle_delete_enabled)

    def update_chosen(self):
        items = self.list_widget.selectedItems()
        self.chosen_line.setText(items[0].text() if items else "")

    def _toggle_delete_enabled(self):
        self.btn_delete.setEnabled(len(self.list_widget.selectedItems()) > 0)
        self.update_chosen()

    def add_element(self):
        text = self.new_line.text().strip()
        if not text:
            return
        # Optional: prevent duplicates. Remove this check if duplicates are desired.
        existing = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if text in existing:
            QMessageBox.information(self, "Info", "Element already exists.")
            return
        self.list_widget.addItem(text)
        self.new_line.clear()
        # Select the newly added item
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def delete_selected(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
            self.update_chosen()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Picker()
    w.resize(480, 360)
    w.show()
    sys.exit(app.exec_())
