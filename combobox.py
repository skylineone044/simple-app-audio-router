from PyQt6.QtWidgets import QComboBox, QSizePolicy
from PyQt6 import QtCore, QtWidgets


class ComboBox(QComboBox):
    popupAboutToBeShown = QtCore.pyqtSignal(name="popupAboutToBeShown")

    def __init__(self, parent=None):
        super().__init__(parent)

    def showPopup(self):
        self.popupAboutToBeShown.emit()
        # print("showing popup!")
        super(ComboBox, self).showPopup()
