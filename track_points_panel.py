from PyQt5.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QMenu, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDockWidget, QMessageBox)
from PyQt5.QtCore import Qt
from point_edit_dialog import PointEditDialog

class TrackPointsPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Body tratě", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.parent = parent
        self.main_widget = QWidget()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["X","Y","Z","Stanice","Výhybka"])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)

        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_center = QPushButton("Zaměřit na vybraný bod")
        self.btn_center.clicked.connect(self.select_point)

        btn_layout.addWidget(self.btn_center)
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)
        self.main_widget.setLayout(layout)
        self.setWidget(self.main_widget)

        self.points = []  # current list of points

    def load_points(self, segments):
        self.points.clear()
        for seg in segments:
            for p in seg.get_points():
                self.points.append(p)

        self.table.setRowCount(len(self.points))
        for i, p in enumerate(self.points):
            self.table.setItem(i,0,QTableWidgetItem(str(p.x)))
            self.table.setItem(i,1,QTableWidgetItem(str(p.y)))
            self.table.setItem(i,2,QTableWidgetItem(str(p.z)))
            self.table.setItem(i,3,QTableWidgetItem(p.station_name if p.station_name else ""))
            self.table.setItem(i,4,QTableWidgetItem(p.switch_name if p.switch_name else ""))

    def on_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            p = self.points[row]

            menu = QMenu(self)
            act_info = menu.addAction("Nastavení bodu")
            chosen = menu.exec_(self.table.mapToGlobal(pos))
            if chosen == act_info:
                dlg = PointEditDialog(p, self)
                if dlg.exec_():
                    self.table.setItem(row,0,QTableWidgetItem(str(p.x)))
                    self.table.setItem(row,1,QTableWidgetItem(str(p.y)))
                    self.table.setItem(row,2,QTableWidgetItem(str(p.z)))
                    self.table.setItem(row,3,QTableWidgetItem(p.station_name if p.station_name else ""))
                    self.table.setItem(row,4,QTableWidgetItem(p.switch_name if p.switch_name else ""))
                    if self.parent:
                        self.parent.update_segments_after_edit(p)
                        self.parent.redraw_scene()

    def select_point(self):
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        p = self.points[row]
        if self.parent:
            self.parent.center_on_point(p)
