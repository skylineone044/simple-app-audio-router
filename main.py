import sys

try:
    from PyQt6 import uic, QtCore
    from PyQt6.QtWidgets import QApplication, QMainWindow, QStyleFactory
except ImportError or ModuleNotFoundError as ie:
    print(ie)
    print("Cannot import PyQT6, exiting...")
    print("Please install PyQT6 using your system's package manager.")
    exit(1)

import pw_interface
import widgets

APP = QApplication(sys.argv)  # the main app instance

# Show error popup if not running on pipewire
if not pw_interface.check_sound_server():
    mess = widgets.NoPipeWireWarningDialog()

    mess.show()
    mess.exec()
    exit(2)

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
    window = widgets.MainWindow(VSM, NM)
    window.show()

    APP.exec()
finally:
    # Terminate all crated virtual sinks on app exit
    VSM.terminate_all()
