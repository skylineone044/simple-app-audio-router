import sys

from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow

import pw_interface
import widgets


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("MainWindow.ui", self)

        self.setWindowTitle("Simple App Audio Router")
        self.routerWidgets = []

        self.addMoreOutputsButton.clicked.connect(self.add_router_widget)

    def add_router_widget(self):
        self.routerWidgets.append(widgets.RouteWidget(self.scrollArea, VSM, NM))
        self.output_list.addWidget(self.routerWidgets[-1], alignment=QtCore.Qt.AlignmentFlag.AlignTop)


app = QApplication(sys.argv)

from PyQt6.QtWidgets import QStyleFactory

AVAILABLE_THEMES = QStyleFactory.keys()
print(f"Available themes: {AVAILABLE_THEMES}")
app.setStyle(AVAILABLE_THEMES[0])
print(f"Current theme: {app.style().objectName()}")
app.setStyleSheet("background-color: rgba(0, 0, 0, 0)")

VSM = pw_interface.VirtualSinkManager()
NM = pw_interface.NodeManager()

try:
    window = MainWindow()
    window.show()

    app.exec()
finally:
    VSM.terminate_all()
