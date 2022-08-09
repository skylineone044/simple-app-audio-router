from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QFrame, QPushButton
from PyQt6 import uic, QtCore

import pw_interface


class ComboBox(QComboBox):
    popupAboutToBeShown = QtCore.pyqtSignal(name="popupAboutToBeShown")

    def __init__(self, parent=None):
        super().__init__(parent)

    def showPopup(self):
        self.popupAboutToBeShown.emit()
        # print("showing popup!")
        super(ComboBox, self).showPopup()


class RouteWidget(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)
        self.app_combobox_height = 32
        self.app_combobox_vbox_padding = 10

        self.app_output_comboboxes = []

        self.add_more_apps_btn.clicked.connect(self.add_app_output_combobox)
        self.removeSinkButton.clicked.connect(self.remove)

        self.add_app_output_combobox()

    def update_app_selection_combobox_items(self, cb: ComboBox):
        cb.clear()
        cb.addItems(
            [" "] + [f"{item_id}: {item_name}" for item_id, item_name in pw_interface.get_node_outputs().items()])

    def remove_app_output_combobox(self, cb):
        # TODO: do not forget to disconnect the app from the virtual sink
        self.app_output_comboboxes.remove(cb)
        cb.setParent(None)

        self.app_list.setFixedHeight(
            len(self.app_output_comboboxes) * self.app_combobox_height + self.app_combobox_vbox_padding)
        self.setFixedHeight(
            max(len(self.app_output_comboboxes) * self.app_combobox_height + 2 * self.app_combobox_vbox_padding, 100))

    def add_app_output_combobox(self):
        hbox = QFrame()
        hbox.setContentsMargins(0, 0, 0, 0)

        self.app_list_vbox.addWidget(hbox, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.app_output_comboboxes.append(hbox)

        hbox_layout = QHBoxLayout()
        hbox.setLayout(hbox_layout)
        hbox.setFixedHeight(self.app_combobox_height)

        cb = ComboBox()
        cb.setFixedHeight(self.app_combobox_height - 7)
        cb.popupAboutToBeShown.connect(
            lambda: self.update_app_selection_combobox_items(cb))

        remove_btn = QPushButton("Remove")
        remove_btn.setFixedHeight(self.app_combobox_height - 7)
        remove_btn.setFixedWidth(60)
        remove_btn.clicked.connect(lambda: self.remove_app_output_combobox(hbox))

        hbox_layout.addWidget(cb)
        hbox_layout.addWidget(remove_btn)

        self.app_list.setFixedHeight(
            len(self.app_output_comboboxes) * self.app_combobox_height + self.app_combobox_vbox_padding)
        self.setFixedHeight(
            max(len(self.app_output_comboboxes) * self.app_combobox_height + 2 * self.app_combobox_vbox_padding, 100))

    def remove(self):
        # TODO: do not forget to close the sink for this widget as well
        self.setParent(None)
