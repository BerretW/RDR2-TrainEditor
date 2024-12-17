import os
import math
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (QMainWindow, QGraphicsView, QMenuBar, QAction, QFileDialog,
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QDockWidget, QVBoxLayout, QWidget, QApplication)
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF, QPoint
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsScene

from track_data import TrackPoint, CurveSegment
from point_edit_dialog import PointEditDialog
from track_points_panel import TrackPointsPanel

class PointGraphicsItem(QGraphicsRectItem):
    # Změna z QGraphicsEllipseItem na QGraphicsRectItem, aby byl výběr konzistentní
    # (může zůstat i QGraphicsEllipseItem, ale to nemá vliv na funkčnost)
    def __init__(self, point, track_name):
        super().__init__()
        self.point = point
        self.point.track_name = track_name
        self.setZValue(10)

class CustomGraphicsScene(QGraphicsScene):
    pass

class TrackEditor(QMainWindow):
    def __init__(self, xml_file="tracks\\traintracks.xml"):
        super().__init__()
        self.setWindowTitle("RDR2 Track Editor - Rozšílená funkcionalita")

        self.current_xml_file = xml_file
        self.tracks = {}
        self.current_track_name = None
        self.point_to_item = {}
        self.selected_points = set()

        # Kamera
        self.cx, self.cy, self.cz = 0.0, 0.0, 100.0  
        self.yaw = 0.0  
        self.move_speed = 5.0
        self.rotate_speed = 5.0

        self.scene = CustomGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        self.init_menu()
        self.init_dock()

        # Dock pro body tratě
        self.points_panel = TrackPointsPanel(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.points_panel)

        self.load_tracks(self.current_xml_file)
        self.redraw_scene()

        self.select_start = None
        self.pan_active = False
        self.last_mouse_pos = None
        self.mouse_moved = False  # sleduje, zda během držení myši došlo k tahu

    def init_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Soubor")

        act_open = QAction("Otevřít traintracks.xml", self)
        act_open.triggered.connect(self.open_xml)
        file_menu.addAction(act_open)

        act_save = QAction("Uložit změny", self)
        act_save.triggered.connect(self.save_changes)
        file_menu.addAction(act_save)

        act_exit = QAction("Konec", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

    def init_dock(self):
        self.dock = QDockWidget("Seznam tratí", self)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.track_list = QTreeWidget()
        self.track_list.setHeaderLabels(["Trať","Viditelné"])
        self.track_list.setColumnCount(2)
        self.track_list.itemChanged.connect(self.on_track_visibility_changed)
        self.track_list.itemDoubleClicked.connect(self.on_track_item_double_clicked)

        dock_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.track_list)
        dock_widget.setLayout(layout)

        self.dock.setWidget(dock_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)

    def open_xml(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Otevřít traintracks.xml", "", "XML soubory (*.xml)")
        if filename:
            self.current_xml_file = filename
            self.tracks.clear()
            self.scene.clear()
            self.point_to_item.clear()
            self.selected_points.clear()
            self.load_tracks(self.current_xml_file)
            self.redraw_scene()
            self.populate_track_list()

    def save_changes(self):
        for tn, data in self.tracks.items():
            dat_file = data["file"]
            segments = data["segments"]

            lines = []
            for seg in segments:
                p = seg.get_points()
                seg.update_station_switch()
                station_part = ""
                if seg.station_name and seg.switch_name:
                    station_part = f"{seg.station_name} 8{seg.switch_name}"
                elif seg.station_name:
                    station_part = seg.station_name
                elif seg.switch_name:
                    station_part = "8"+seg.switch_name

                line = f"c {p[0].x} {p[0].y} {p[0].z} {p[1].x} {p[1].y} {p[1].z} {p[2].x} {p[2].y} {p[2].z} 0 0"
                if station_part:
                    line += " " + station_part
                lines.append(line)

            try:
                with open(dat_file, "w", encoding="utf-8") as f:
                    for l in lines:
                        f.write(l+"\n")
                print(f"Uloženo: {dat_file}")
            except Exception as e:
                QMessageBox.warning(self, "Chyba", f"Nepodařilo se uložit {dat_file}:\n{e}")
        QMessageBox.information(self, "Uloženo", "Změny byly uloženy.")

    def populate_track_list(self):
        self.track_list.clear()
        for tn, data in self.tracks.items():
            item = QTreeWidgetItem([tn])
            item.setCheckState(1, Qt.Checked if data["visible"] else Qt.Unchecked)
            self.track_list.addTopLevelItem(item)

    def load_tracks(self, xml_file):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
        except Exception as e:
            QMessageBox.warning(self, "Chyba", f"Nelze načíst XML: {e}")
            return

        for track in root.findall('train_track'):
            full_path = track.get('filename')
            if full_path is None:
                continue
            track_file = os.path.basename(full_path)
            if not os.path.exists(track_file):
                track_file = os.path.join(os.path.dirname(xml_file), track_file)

            print(f"Načítám: {track_file}")
            segments = self.load_dat(track_file)
            if segments:
                track_name = track.get('trainConfigName', track_file)
                self.tracks[track_name] = {
                    "file": track_file,
                    "segments": segments,
                    "visible": True
                }

        self.populate_track_list()

    def load_dat(self, dat_file):
        segments = []
        if not os.path.exists(dat_file):
            print(f"Soubor {dat_file} neexistuje!")
            return segments
        try:
            with open(dat_file, "r", encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if line.startswith('c '):
                        parts = line.split()
                        if len(parts) < 11:
                            continue
                        try:
                            x1, y1, z1 = float(parts[1]), float(parts[2]), float(parts[3])
                            x2, y2, z2 = float(parts[4]), float(parts[5]), float(parts[6])
                            x3, y3, z3 = float(parts[7]), float(parts[8]), float(parts[9])
                        except ValueError:
                            continue
                        tail = parts[10:]
                        if len(tail) < 2:
                            length_val = 0
                            flag_val = 0
                            remain = []
                        else:
                            length_val = tail[0]
                            flag_val = tail[1]
                            remain = tail[2:]

                        station_name = None
                        switch_name = None
                        for t in remain:
                            if t.startswith('8'):
                                switch_name = t[1:]
                            else:
                                station_name = t

                        seg = CurveSegment(
                            TrackPoint(x1, y1, z1, station_name, switch_name),
                            TrackPoint(x2, y2, z2, station_name, switch_name),
                            TrackPoint(x3, y3, z3, station_name, switch_name),
                            station_name=station_name,
                            switch_name=switch_name
                        )
                        segments.append(seg)
        except Exception as e:
            print("Chyba při načítání DAT souboru:", e)
        
        return segments

    def on_track_visibility_changed(self, item, column):
        if column == 1:
            track_name = item.text(0)
            visible = (item.checkState(1) == Qt.Checked)
            self.set_track_visibility(track_name, visible)

    def set_track_visibility(self, track_name, visible):
        self.tracks[track_name]["visible"] = visible
        self.redraw_scene()

    def on_track_item_double_clicked(self, item, column):
        track_name = item.text(0)
        data = self.tracks[track_name]
        # Načteme body do panelu
        self.points_panel.load_points(data["segments"])
        self.current_track_name = track_name

    def center_on_point(self, p):
        self.cx = p.x
        self.cy = p.y
        self.redraw_scene()

    def redraw_scene(self):
        self.scene.clear()
        self.point_to_item.clear()
        self.rubber_band_item = QGraphicsRectItem()
        self.rubber_band_item.setPen(QPen(Qt.blue, 1, Qt.DashLine))
        self.rubber_band_item.setBrush(QBrush(QColor(0,0,255,50)))
        self.rubber_band_item.setZValue(50)
        self.rubber_band_item.hide()
        self.scene.addItem(self.rubber_band_item)

        pen = QPen(Qt.black)
        pen.setWidth(2)

        for tn, data in self.tracks.items():
            if not data["visible"]:
                continue
            segments = data["segments"]
            for seg in segments:
                self.draw_curve_segment(seg, pen, track_name=tn)

        self.view.setSceneRect(self.scene.itemsBoundingRect())

    def draw_curve_segment(self, segment, pen, track_name):
        p1 = self.project_point(segment.p1.x, segment.p1.y, segment.p1.z)
        p2 = self.project_point(segment.p2.x, segment.p2.y, segment.p2.z)
        p3 = self.project_point(segment.p3.x, segment.p3.y, segment.p3.z)

        self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
        self.scene.addLine(p2.x(), p2.y(), p3.x(), p3.y(), pen)

        self.create_point_item(segment.p1, track_name)
        self.create_point_item(segment.p2, track_name)
        self.create_point_item(segment.p3, track_name)

    def create_point_item(self, point, track_name):
        pt_2d = self.project_point(point.x, point.y, point.z)
        item = PointGraphicsItem(point, track_name)
        item.setRect(pt_2d.x()-3, pt_2d.y()-3, 6, 6)
        item.setBrush(QBrush(Qt.red))
        self.scene.addItem(item)
        self.point_to_item[point] = item
        if point in self.selected_points:
            item.setBrush(QBrush(Qt.green))

    def project_point(self, x, y, z):
        dx = x - self.cx
        dy = y - self.cy
        dz = z - self.cz
        cos_y = math.cos(math.radians(self.yaw))
        sin_y = math.sin(math.radians(self.yaw))
        x2 = dx*cos_y + dy*sin_y
        y2 = -dx*sin_y + dy*cos_y
        return QPointF(x2, y2)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_W:
            self.cx += self.move_speed*math.cos(math.radians(self.yaw))
            self.cy += self.move_speed*math.sin(math.radians(self.yaw))
        elif event.key() == Qt.Key_S:
            self.cx -= self.move_speed*math.cos(math.radians(self.yaw))
            self.cy -= self.move_speed*math.sin(math.radians(self.yaw))
        elif event.key() == Qt.Key_A:
            self.cx += self.move_speed*math.cos(math.radians(self.yaw-90))
            self.cy += self.move_speed*math.sin(math.radians(self.yaw-90))
        elif event.key() == Qt.Key_D:
            self.cx += self.move_speed*math.cos(math.radians(self.yaw+90))
            self.cy += self.move_speed*math.sin(math.radians(self.yaw+90))
        elif event.key() == Qt.Key_Q:
            self.cz += self.move_speed
        elif event.key() == Qt.Key_E:
            self.cz -= self.move_speed
        elif event.key() == Qt.Key_Left:
            self.yaw -= self.rotate_speed
        elif event.key() == Qt.Key_Right:
            self.yaw += self.rotate_speed

        self.redraw_scene()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select_start = event.pos()
            self.rubber_band_item.setRect(QRectF(self.select_start, self.select_start))
            self.rubber_band_item.show()
            self.mouse_moved = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.select_start is not None:
            rect = QRectF(self.select_start, event.pos()).normalized()
            self.rubber_band_item.setRect(rect)
            self.mouse_moved = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.select_start is not None:
            rect = QRectF(self.select_start, event.pos()).normalized()
            self.rubber_band_item.hide()

            # pokud se myš téměř nepohnula, bereme to jako klik
            if not self.mouse_moved or rect.width() < 2 and rect.height() < 2:
                # zkusíme vybrat bod pod kurzorem
                scene_pos = self.view.mapToScene(event.pos())
                items = self.scene.items(scene_pos)
                # najdeme první PointGraphicsItem
                clicked_points = set()
                for it in items:
                    if isinstance(it, PointGraphicsItem):
                        # nalezen bod
                        clicked_points.add(it.point)
                        break

                self.apply_selection(clicked_points)
            else:
                # standardní obdélníkový výběr
                self.select_points_in_rect(rect)

            self.select_start = None
        super().mouseReleaseEvent(event)

    def select_points_in_rect(self, rect):
        mods = QApplication.keyboardModifiers()
        add_mode = bool(mods & Qt.ControlModifier)
        remove_mode = bool(mods & Qt.AltModifier)

        new_selection = set()
        for p, it in self.point_to_item.items():
            center = self.view.mapFromScene(it.sceneBoundingRect().center())
            if rect.contains(center):
                new_selection.add(p)

        self.apply_selection(new_selection, add_mode, remove_mode)

    def apply_selection(self, new_selection, add_mode=False, remove_mode=False):
        if add_mode:
            self.selected_points |= new_selection
        elif remove_mode:
            self.selected_points -= new_selection
        else:
            self.selected_points = new_selection

        for p, it in self.point_to_item.items():
            if p in self.selected_points:
                it.setBrush(QBrush(Qt.green))
            else:
                it.setBrush(QBrush(Qt.red))

    def mouseDoubleClickEvent(self, event):
        scene_pos = self.view.mapToScene(event.pos())
        items = self.scene.items(scene_pos)
        for it in items:
            if isinstance(it, PointGraphicsItem):
                p = it.point
                dlg = PointEditDialog(p, self)
                if dlg.exec_():
                    self.update_segments_after_edit(p)
                    self.redraw_scene()
                break
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        # Zoom kolečkem myši
        angle = event.angleDelta().y()
        factor = 1.1 if angle > 0 else 1.0/1.1
        self.view.scale(factor, factor)
