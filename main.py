import sys

from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow, QStyleFactory

import pw_interface
import widgets


class MainWindow(QMainWindow):
    """
    MainWindow: The main window where all the other widgets are displayed in
    """

    def __init__(self):
        super().__init__()
        uic.loadUi("MainWindow.ui", self)  # Load the "MainWindow.ui" file, which was made using QT Designer

        self.setWindowTitle("Simple App Audio Router")
        self.routerWidgets = []  # Store all the routeWidgets that are displayed

        # the button that adds one more routeWidget ot the window
        self.addMoreOutputsButton.clicked.connect(self.add_router_widget)

    def add_router_widget(self) -> None:
        """
        Add a new RouteWidget instance to the self.routeWidgets list, and add it to the mainWindow's output_list
        widget to be displayed

        :return: None
        """
        self.routerWidgets.append(widgets.RouteWidget(self.scrollArea, VSM, NM))
        self.output_list.addWidget(self.routerWidgets[-1], alignment=QtCore.Qt.AlignmentFlag.AlignTop)


APP = QApplication(sys.argv)  # the main app instance

AVAILABLE_THEMES = QStyleFactory.keys()  # get a list of available themes
print(f"Available themes: {AVAILABLE_THEMES}")
APP.setStyle(AVAILABLE_THEMES[0])  # pick the first available theme
print(f"Current theme: {APP.style().objectName()}")
# set the main background to be transparent (my default theme uses transparent window backgrounds,
# without this it would be opaque)
APP.setStyleSheet("background-color: rgba(0, 0, 0, 0)")

# the VirtualSinkManager manages the virtual sinks crated and destroyed by the routeWidgets
VSM = pw_interface.VirtualSinkManager()

# the NodeManager manages the nodes, ports and links in the pipewire graph
NM = pw_interface.NodeManager()

try:
    window = MainWindow()
    window.show()

    APP.exec()
finally:
    # Terminate all crated virtual sinks on app exit
    VSM.terminate_all()
