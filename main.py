from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PyQt6 import uic

import sys


class RouteWidget(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)
        print(f"{self.removeButton=}")



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple App Audio Router")

        r1 = RouteWidget()

        # Set the central widget of the Window.
        main_widget = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(r1)
        main_widget.setLayout(vbox)
        self.setCentralWidget(main_widget)


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
