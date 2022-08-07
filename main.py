from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PyQt6 import uic

import sys

import pw_interface


class RouteWidget(QWidget):
    def __init__(self):
        super().__init__()
        print("creating new RouteWidget...")
        uic.loadUi("RouteWidget.ui", self)

        self.update_app_selection_combobox_items()

        # refresh the list of available outputs after the user selects one from the list.
        # It would be best to refresh the items when the user opens the combobox, but I have not found an easy way to do so
        # self.newAppComboBox.activated.connect(self.update_app_selection_combobox_items)
        self.refreshOutputListButton.clicked.connect(self.update_app_selection_combobox_items)

        self.removeSinkButton.clicked.connect(self.remove)

    def update_app_selection_combobox_items(self):
        print("updating combobox items....")
        self.newAppComboBox.clear()
        self.newAppComboBox.addItems([" "] + [f"{item_id}: {item_name}" for item_id, item_name in pw_interface.get_node_outputs().items()])

    def remove(self):
        ## do not forget to close the sink for this widget as well
        self.setParent(None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple App Audio Router")
        routerWidgets = []

        addMoreOutputsButton = QPushButton("Add another output")
        addMoreOutputsButton.setFixedWidth(200)
        addMoreOutputsButton.clicked.connect(self.add_router_widget)

        # Set the central widget of the Window.
        main_widget = QWidget()
        vbox = QVBoxLayout()
        main_widget.setLayout(vbox)


        vbox.addWidget(addMoreOutputsButton)
        self.setCentralWidget(main_widget)

    def add_router_widget(self):
        print("adding new router...")
        self.routerWidgets.append(RouteWidget())
        print(self.routerWidgets)
        print("adding new router to display...")
        self.vbox.addWidget(self.routerWidgets[-1])

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

