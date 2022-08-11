from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QFrame, QPushButton

import pw_interface


class ComboBox(QComboBox):
    popupAboutToBeShown = QtCore.pyqtSignal(name="popupAboutToBeShown")

    def __init__(self, scrollWidget=None, *args, **kwargs):
        super(ComboBox, self).__init__(*args, **kwargs)
        self.scroll_with_strong_focus = False

        self.scrollWidget = scrollWidget
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, *args, **kwargs):
        if self.hasFocus() and self.scroll_with_strong_focus:
            return QComboBox.wheelEvent(self, *args, **kwargs)
        else:
            return self.scrollWidget.wheelEvent(*args, **kwargs)

    def showPopup(self):
        self.popupAboutToBeShown.emit()
        # print("showing popup!")
        super(ComboBox, self).showPopup()


class RouteWidget(QWidget):
    def __init__(self, scrollWidget=None, virtual_sink_manager: pw_interface.VirtualSinkManager = None,
                 node_manager: pw_interface.NodeManager = None):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)
        self.parent_scrollWidget = scrollWidget
        self.virtual_sink_manager = virtual_sink_manager
        self.node_manager = node_manager

        self.app_combobox_height = 32
        self.app_combobox_vbox_padding = 10

        self.app_output_comboboxes = []

        self.add_more_apps_btn.clicked.connect(self.add_app_output_combobox)
        self.remove_sink_button.clicked.connect(self.remove)

        self.add_app_output_combobox()

        self.virtual_sink = self.virtual_sink_manager.create_virtual_sink()
        self.sink_name_label.setText(self.virtual_sink.name)

    def update_app_selection_combobox_items(self, cb: ComboBox):
        cb.clear()
        self.node_manager.update()
        cb.addItems(
            [" "] + [f"{node_id}: {node.get_readable_name()}" for node_id, node in
                     self.node_manager.get_nodes("Source").items()])

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

        cb = ComboBox(scrollWidget=self.parent_scrollWidget)
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
        self.virtual_sink_manager.remove(self.virtual_sink)
        self.setParent(None)
