from PyQt6.QtWidgets import QWidget, QComboBox
from PyQt6 import uic, QtCore


class ComboBox(QComboBox):
    popupAboutToBeShown = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def showPopup(self):
        self.popupAboutToBeShown.emit()
        # print("showing popup!")
        super(ComboBox, self).showPopup()
