from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QVBoxLayout, QMessageBox

class PointEditDialog(QDialog):
    def __init__(self, point, parent=None):
        super().__init__(parent)
        self.point = point
        self.setWindowTitle("Úprava bodu")

        self.x_edit = QLineEdit(str(point.x))
        self.y_edit = QLineEdit(str(point.y))
        self.z_edit = QLineEdit(str(point.z))
        self.station_edit = QLineEdit(point.station_name if point.station_name else "")
        self.switch_edit = QLineEdit(point.switch_name if point.switch_name else "")

        form = QFormLayout()
        form.addRow("X:", self.x_edit)
        form.addRow("Y:", self.y_edit)
        form.addRow("Z:", self.z_edit)
        form.addRow("Stanice:", self.station_edit)
        form.addRow("Výhybka:", self.switch_edit)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Storno")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_box)
        self.setLayout(layout)

    def accept(self):
        try:
            self.point.x = float(self.x_edit.text())
            self.point.y = float(self.y_edit.text())
            self.point.z = float(self.z_edit.text())
            self.point.station_name = self.station_edit.text().strip() if self.station_edit.text().strip() else None
            self.point.switch_name = self.switch_edit.text().strip() if self.switch_edit.text().strip() else None
        except ValueError:
            QMessageBox.warning(self, "Chyba", "Neplatné číselné hodnoty pro X, Y nebo Z!")
            return
        super().accept()
