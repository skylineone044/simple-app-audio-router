from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QSizePolicy
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PyQt6 import QtWidgets, uic

import sys

import pw_interface
import combobox


class RouteWidget(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)
        self.app_output_comboboxes = []

        self.addMoreAppsButton.clicked.connect(self.add_app_output_combobox)
        self.removeSinkButton.clicked.connect(self.remove)

        self.add_app_output_combobox()

    def update_app_selection_combobox_items(self, cb: combobox.ComboBox):
        cb.clear()
        cb.addItems(
            [" "] + [f"{item_id}: {item_name}" for item_id, item_name in pw_interface.get_node_outputs().items()])

    def add_app_output_combobox(self):
        cb = combobox.ComboBox()
        cb.setFixedHeight(25)
        self.appOutputs.addWidget(cb)
        print(f"{self.verticalLayout.sizeHint()}")
        self.setMinimumHeight(max(self.verticalLayout.sizeHint().height() + 50, 120))

        cb.popupAboutToBeShown.connect(
            lambda: self.update_app_selection_combobox_items(cb))
        self.app_output_comboboxes.append(cb)


    def remove(self):
        ## do not forget to close the sink for this widget as well
        self.setParent(None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("MainWindow.ui", self)

        self.setWindowTitle("Simple App Audio Router")
        self.routerWidgets = []

        self.addMoreOutputsButton.clicked.connect(self.add_router_widget)

    def add_router_widget(self):
        self.routerWidgets.append(RouteWidget())
        self.output_list.addWidget(self.routerWidgets[-1])


app = QApplication(sys.argv)

from PyQt6.QtWidgets import QStyleFactory

AVAILABLE_THEMES = QStyleFactory.keys()
print(f"Available themes: {AVAILABLE_THEMES}")
app.setStyle(AVAILABLE_THEMES[0])
app.setStyleSheet("background-color: rgba(0, 0, 0, 0)")
print(f"Current theme: {app.style().objectName()}")

window = MainWindow()
window.show()

app.exec()
