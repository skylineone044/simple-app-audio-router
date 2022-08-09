from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6 import uic, QtCore

import sys
import json

import time

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
        self.routerWidgets.append(widgets.RouteWidget(self.scrollArea))
        self.output_list.addWidget(self.routerWidgets[-1], alignment=QtCore.Qt.AlignmentFlag.AlignTop)


app = QApplication(sys.argv)

from PyQt6.QtWidgets import QStyleFactory

AVAILABLE_THEMES = QStyleFactory.keys()
print(f"Available themes: {AVAILABLE_THEMES}")
app.setStyle(AVAILABLE_THEMES[0])
print(f"Current theme: {app.style().objectName()}")
app.setStyleSheet("background-color: rgba(0, 0, 0, 0)")

print("Outputs: " + json.dumps(pw_interface.get_node_outputs(), indent=4))
print("Inputs: " + json.dumps(pw_interface.get_node_inputs(), indent=4))
# print(f"{pw_interface.get_node_links()=}")

window = MainWindow()
window.show()

app.exec()
