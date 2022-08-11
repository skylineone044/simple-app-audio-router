from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QFrame, QPushButton

import pw_interface


class ComboBox(QComboBox):
    popupAboutToBeShown = QtCore.pyqtSignal(name="popupAboutToBeShown")

    def __init__(self,
                 scrollWidget=None,
                 node_manager: pw_interface.NodeManager = None,
                 app_node: pw_interface.Node = None,
                 parent_sink_node: pw_interface.Node = None,
                 parent=None):
        super(ComboBox, self).__init__(parent)
        self.scroll_with_strong_focus = False
        self.scrollWidget = scrollWidget
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.node_manager: pw_interface.NodeManager = node_manager
        self.app_node: pw_interface.Node | None = app_node
        self.parent_sink_node: pw_interface.Node = parent_sink_node

        self.last_selected: str = " "
        self.activated.connect(self.on_activated)

    def on_activated(self) -> None:
        new_selection: str = str(self.currentText())
        print(f"activating: {new_selection}")
        new_selection_node_id: int = int(new_selection.split(":")[0])
        if self.last_selected == " ":
            # print("last was empty")
            self.app_node = self.node_manager.get_nodes("Source")[new_selection_node_id]
            self.node_manager.connect_nodes(self.app_node, self.parent_sink_node)
        else:
            # print("last was not empty")
            self.disconnect_app_node()
            self.app_node = self.node_manager.get_nodes("Source")[new_selection_node_id]
            self.node_manager.connect_nodes(self.app_node, self.parent_sink_node)

        self.last_selected = new_selection

    def disconnect_app_node(self) -> None:
        self.node_manager.disconnect_nodes(self.app_node, self.parent_sink_node)
        self.app_node = None

    def wheelEvent(self, *args, **kwargs):
        if self.hasFocus() and self.scroll_with_strong_focus:
            return QComboBox.wheelEvent(self, *args, **kwargs)
        else:
            return self.scrollWidget.wheelEvent(*args, **kwargs)

    def showPopup(self) -> None:
        self.popupAboutToBeShown.emit()
        # print("showing popup!")
        super(ComboBox, self).showPopup()


class RouteWidget(QWidget):
    def __init__(self, scrollWidget=None, virtual_sink_manager: pw_interface.VirtualSinkManager = None,
                 node_manager: pw_interface.NodeManager = None):
        super().__init__()
        uic.loadUi("RouteWidget.ui", self)
        self.parent_scrollWidget = scrollWidget
        self.node_manager: pw_interface.NodeManager = node_manager

        self.virtual_sink_manager: pw_interface.VirtualSinkManager = virtual_sink_manager
        self.virtual_sink: pw_interface.VirtualSink = self.virtual_sink_manager.create_virtual_sink()
        self.sink_name_label.setText(self.virtual_sink.name)

        self.app_combobox_height: int = 32
        self.app_combobox_vbox_padding: int = 10

        self.app_output_comboboxes: [QFrame] = []

        self.add_more_apps_btn.clicked.connect(self.add_app_output_combobox)
        self.remove_sink_button.clicked.connect(self.remove)

        self.output_sink_node: pw_interface.Node = node_manager.get_loopback_sink_node(self.virtual_sink)
        self.app_nodes: dict[int, pw_interface.Node] = {}

        self.add_app_output_combobox()

    def update_app_selection_combobox_items(self, cb: ComboBox) -> None:
        cb.clear()
        self.node_manager.update()
        cb.addItems(
            [" "] + [f"{node_id}: {node.get_readable_name()}" for node_id, node in
                     self.node_manager.get_nodes("Source").items()])

    def remove_app_output_combobox(self, cb_frame: QFrame) -> None:
        cb_frame.findChild(ComboBox).disconnect_app_node()
        self.app_output_comboboxes.remove(cb_frame)
        cb_frame.setParent(None)

        self.app_list.setFixedHeight(
            len(self.app_output_comboboxes) * self.app_combobox_height + self.app_combobox_vbox_padding)
        self.setFixedHeight(
            max(len(self.app_output_comboboxes) * self.app_combobox_height + 2 * self.app_combobox_vbox_padding, 100))

    def add_app_output_combobox(self) -> None:
        hbox: QFrame = QFrame()
        hbox.setContentsMargins(0, 0, 0, 0)

        self.app_list_vbox.addWidget(hbox, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.app_output_comboboxes.append(hbox)

        hbox_layout: QHBoxLayout = QHBoxLayout()
        hbox.setLayout(hbox_layout)
        hbox.setFixedHeight(self.app_combobox_height)

        cb: ComboBox = ComboBox(scrollWidget=self.parent_scrollWidget, node_manager=self.node_manager, app_node=None,
                      parent_sink_node=self.output_sink_node)
        cb.setFixedHeight(self.app_combobox_height - 7)
        cb.popupAboutToBeShown.connect(
            lambda: self.update_app_selection_combobox_items(cb))

        remove_btn: QPushButton = QPushButton("Remove")
        remove_btn.setFixedHeight(self.app_combobox_height - 7)
        remove_btn.setFixedWidth(60)
        remove_btn.clicked.connect(lambda: self.remove_app_output_combobox(hbox))

        hbox_layout.addWidget(cb)
        hbox_layout.addWidget(remove_btn)

        self.app_list.setFixedHeight(
            len(self.app_output_comboboxes) * self.app_combobox_height + self.app_combobox_vbox_padding)
        self.setFixedHeight(
            max(len(self.app_output_comboboxes) * self.app_combobox_height + 2 * self.app_combobox_vbox_padding, 100))

    def remove(self) -> None:
        self.virtual_sink_manager.remove(self.virtual_sink)
        self.setParent(None)
