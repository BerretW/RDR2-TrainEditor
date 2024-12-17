import sys
from PyQt5.QtWidgets import QApplication
from track_editor import TrackEditor

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrackEditor(xml_file="tracks\traintracks.xml")
    window.show()
    sys.exit(app.exec_())
