from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PyQt6 import uic

import sys

import pw_interface


class RouteWidget(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)

        self.update_app_selection_combobox_items()

        # refresh the list of available outputs after the user selects one from the list.
        # It would be best to refresh the items when the user opens the combobox, but I have not found an easy way to do so
        # self.newAppComboBox.activated.connect(self.update_app_selection_combobox_items)
        self.refreshOutputListButton.clicked.connect(self.update_app_selection_combobox_items)

        self.removeSinkButton.clicked.connect(self.remove)

    def update_app_selection_combobox_items(self):
        self.newAppComboBox.clear()
        self.newAppComboBox.addItems([" "] + [f"{item_id}: {item_name}" for item_id, item_name in pw_interface.get_node_outputs().items()])

    def remove(self):
        ## do not forget to close the sink for this widget as well
        self.setParent(None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple App Audio Router")
        self.routerWidgets = []

        self.addMoreOutputsButton = QPushButton("Add another output")
        self.addMoreOutputsButton.setFixedWidth(200)
        self.addMoreOutputsButton.clicked.connect(self.add_router_widget)

        # Set the central widget of the Window.
        self.main_widget = QWidget()
        self.vbox = QVBoxLayout()
        self.outputs_vbox = QVBoxLayout()
        self.vbox.addLayout(self.outputs_vbox)
        self.main_widget.setLayout(self.vbox)

        self.vbox.addWidget(self.addMoreOutputsButton)
        self.setCentralWidget(self.main_widget)

    def add_router_widget(self):
        self.routerWidgets.append(RouteWidget())
        self.outputs_vbox.addWidget(self.routerWidgets[-1])

app = QApplication(sys.argv)

from PyQt6.QtWidgets import QStyleFactory

AVAILABLE_THEMES = QStyleFactory.keys()
print(f"Available themes: {AVAILABLE_THEMES}")
app.setStyle(AVAILABLE_THEMES[0])
app.setStyleSheet("background-color: rgba(0, 0, 0, 0)")
print(f"Current theme: {app.style().objectName()}")

window = MainWindow()
window.resize(950, 400)
window.show()

app.exec()

