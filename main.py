from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PyQt6 import QtWidgets, uic, QtCore

import sys

import pw_interface
import combobox


class RouteWidget(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)
        self.app_output_comboboxes = []

        self.add_more_apps_btn.clicked.connect(self.add_app_output_combobox)
        self.removeSinkButton.clicked.connect(self.remove)

        self.add_app_output_combobox()

    def update_app_selection_combobox_items(self, cb: combobox.ComboBox):
        cb.clear()
        cb.addItems(
            [" "] + [f"{item_id}: {item_name}" for item_id, item_name in pw_interface.get_node_outputs().items()])

    def remove_app_output_combobox(self, cb):
        vpadding = 25
        # TODO: do not forget to disconnect the app from the virtual sink
        self.app_output_comboboxes.remove(cb)
        cb.setParent(None)

        self.app_list.setFixedHeight(self.app_list_vbox.sizeHint().height() + vpadding)
        self.setFixedHeight(max(self.app_list_vbox.sizeHint().height() + vpadding, 80))


    def add_app_output_combobox(self):
        hbox = QFrame()
        hbox.setContentsMargins(0, 0, 0, 0)
        height = 32

        self.app_list_vbox.addWidget(hbox, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.app_output_comboboxes.append(hbox)

        hbox_layout = QHBoxLayout()
        hbox.setLayout(hbox_layout)
        hbox.setFixedHeight(height)

        cb = combobox.ComboBox()
        cb.setFixedHeight(height - 7)
        cb.popupAboutToBeShown.connect(
            lambda: self.update_app_selection_combobox_items(cb))

        remove_btn = QPushButton("Remove")
        remove_btn.setFixedHeight(height - 7)
        remove_btn.setFixedWidth(60)
        remove_btn.clicked.connect(lambda: self.remove_app_output_combobox(hbox))

        hbox_layout.addWidget(cb)
        hbox_layout.addWidget(remove_btn)

        vpadding = 10
        self.app_list.setFixedHeight(len(self.app_output_comboboxes) * height + vpadding)
        self.setFixedHeight(max(len(self.app_output_comboboxes) * height + 2 * vpadding, 100))



    def remove(self):
        # TODO: do not forget to close the sink for this widget as well
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
        self.output_list.addWidget(self.routerWidgets[-1], alignment=QtCore.Qt.AlignmentFlag.AlignTop)


app = QApplication(sys.argv)

from PyQt6.QtWidgets import QStyleFactory

AVAILABLE_THEMES = QStyleFactory.keys()
print(f"Available themes: {AVAILABLE_THEMES}")
app.setStyle(AVAILABLE_THEMES[0])
print(f"Current theme: {app.style().objectName()}")
app.setStyleSheet("background-color: rgba(0, 0, 0, 0)")

window = MainWindow()
window.show()

app.exec()
