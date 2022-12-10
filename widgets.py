from PyQt6 import uic, QtCore
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QMainWindow, QComboBox, QWidget, QHBoxLayout, QFrame, QPushButton, QDialog

import pw_interface


class NoPipeWireWarningDialog(QDialog):
    """
    Error popup to inform the user pipewire is not running
    it loads the ui from "ui/NoPipewireDialog.ui"
    """

    def __init__(self):
        super().__init__()
        uic.loadUi("ui/NoPipewireDialog.ui", self)
        self.setWindowTitle("Pipewire not found")


class MainWindow(QMainWindow):
    """
    MainWindow: The main window where all the other widgets are displayed in
    """

    def __init__(self, virtual_sink_manager: pw_interface.VirtualSinkManager = None,
                 node_manager: pw_interface.NodeManager = None):
        """
        Crates a new Mainwindow

        :param virtual_sink_manager: the VirtualSinkManager instance that will manage the virtual loopback devices
        :param node_manager: the NodeManager instance that will handle listing, connecting and disconnecting all the
        right nodes
        """
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)  # Load the "ui/MainWindow.ui" file, which was made using QT Designer

        self.setWindowTitle("Simple App Audio Router")
        self.routerWidgets: [RouteWidget] = []  # Store all the routeWidgets that are displayed
        # Store all Comboboxes, so that when the ports that are in the node that is connected to it are removed from
        # the pipewire graph, the selection of the combobox can be reset to " "
        self.app_combobox_holder: [[QFrame]] = []

        self.virtual_sink_manager = virtual_sink_manager
        self.node_manager = node_manager

        # the button that adds one more routeWidget ot the window
        self.addMoreOutputsButton.clicked.connect(self.add_router_widget)

        print("starting monitor process...")
        self.monitor_proc = QProcess()
        self.monitor_proc.readyReadStandardOutput.connect(self.monitor_proc_stdout)
        self.monitor_proc.start("/usr/bin/pw-link", ["--output", "--monitor", "--id"])

    def add_router_widget(self) -> None:
        """
        Add a new RouteWidget instance to the self.routeWidgets list, and add it to the mainWindow's output_list
        widget to be displayed

        :return: None
        """
        self.routerWidgets.append(
            RouteWidget(self.scrollArea, self.virtual_sink_manager, self.node_manager, self.app_combobox_holder))
        self.output_list.addWidget(self.routerWidgets[-1], alignment=QtCore.Qt.AlignmentFlag.AlignTop)

    def monitor_proc_stdout(self) -> None:
        """
        Monitor the output of "pw-link --output --monitor --id" so when a port is removed from the pipewire graph,
        for example when the application that used the port stops playing audio and removed its nodes, the
        Combobox that had that app selected can be reset

        This function is called by QT in the event loop automatically when new output appears on the stdout of the
        started pw-link process

        :return: None
        """
        data = self.monitor_proc.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        print(stdout)
        if stdout.startswith("-"):
            removed_port_id = int(stdout.split()[1])
            for frames in self.app_combobox_holder:
                for frame in frames:
                    frame.findChild(ComboBox).disconnect_app_node_if_contains_port_id(removed_port_id)


class ComboBox(QComboBox):
    """
    A combobox that has its scrolling disabled (it passes scroll events through to the main window's scrollWidget,
    to scroll the page instead of selecting a new item)
    It also connects / disconnects the apps from the virtual sink using the node_manager
    """

    # the signal that is emitted before the app selection list is shown, used to refresh the list before displaying
    popupAboutToBeShown = QtCore.pyqtSignal(name="popupAboutToBeShown")

    def __init__(self, scrollWidget=None, node_manager: pw_interface.NodeManager = None,
                 app_node: pw_interface.Node = None, parent_sink_node: pw_interface.Node = None, parent=None,
                 isAppSourceCB=True):
        """
        Creates a new Combobox

        :param scrollWidget: the main window's scrollWidget instance
        :param node_manager: the App's NodeManager instance
        :param app_node: the node instance this combobox has selected (can be None if no node is selected)
        :param parent_sink_node: the Node of the VirtualSink to which this combobox's selected app node is connected
        :param parent: QT specific: None by default
        """
        super(ComboBox, self).__init__(parent)
        self.scroll_with_strong_focus = False
        self.scrollWidget = scrollWidget
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.node_manager: pw_interface.NodeManager = node_manager
        self.app_node: pw_interface.Node | None = app_node
        self.parent_sink_node: pw_interface.Node = parent_sink_node

        self.last_selected: str = " "  # when the combobox is created, no app is selected by defualt
        self.activated.connect(self.on_activated)
        self.isAppSourceCB = isAppSourceCB

    def on_activated(self) -> None:
        """
        Activated when a new app is selected from the dropdown list
        Disconnects the previously selected node from the virtual sink (if one was connected) and connects the newly
        selected node to the virtual sink

        :return: None
        """
        new_selection: str = str(self.currentText())
        print(f"activating: {new_selection}")
        if new_selection == " ":  # if the new selection is the "no app" item, then just disconnect the current one
            self.disconnect_app_node()
        else:  # if the new selection is an app
            # the node id of the apps is the first number before the colon
            # for example: node_id: node_name (app_name): media_name
            # for example: 999: Firefox (Firefox): AudioStream
            #     but usually the node_name and the app_name are the same,
            #     so in such cases its shortened to just: 999: Firefox: AudioStream
            new_selection_node_id: int = int(new_selection.split(":")[0])
            if self.last_selected == " ":  # No node was connected previously
                # print("last was empty")
                self.app_node = self.node_manager.get_nodes("Source" if self.isAppSourceCB else "Sink")[
                    new_selection_node_id]  # get new node
                if not pw_interface.connect_nodes_replace_connection(self.app_node,
                                                                     self.parent_sink_node,
                                                                     self.node_manager,
                                                                     reverse_order=not self.isAppSourceCB,
                                                                     replace_connection=not self.isAppSourceCB):  # connect new node to virtual sink
                    self.disconnect_app_node()
                else:
                    self.setCurrentText(new_selection)
            else:  # something was selected previously
                # print("last was not empty")
                if self.last_selected != new_selection:
                    self.disconnect_app_node()  # disconnects the previously selected node
                    self.app_node = self.node_manager.get_nodes("Source" if self.isAppSourceCB else "Sink")[
                        new_selection_node_id]  # get new node
                    if not pw_interface.connect_nodes_replace_connection(self.app_node,
                                                                         self.parent_sink_node,
                                                                         self.node_manager,
                                                                         reverse_order=not self.isAppSourceCB,
                                                                         replace_connection=not self.isAppSourceCB):  # connect new node to virtual sink
                        self.disconnect_app_node()
                    else:
                        self.setCurrentText(new_selection)

        self.last_selected = new_selection  # update last selection to the current one

    def disconnect_app_node(self) -> None:
        """
        Disconnects the currently connected app node form the virtual sink

        :return: None
        """
        if not self.isAppSourceCB and self.app_node:
            pw_interface.disconnect_all_inputs(self.app_node, self.node_manager)
        if self.app_node:
            pw_interface.disconnect_nodes(self.app_node, self.parent_sink_node)
        self.app_node = None
        self.last_selected = " "
        self.setCurrentText(" ")

    def disconnect_app_node_if_contains_port_id(self, disconnected_port_id: int) -> None:
        """
        Disconnect the node of this combobox if the node contains the port specified in the parameter

        :param disconnected_port_id: the port that is searched for
        :return: None
        """
        if self.app_node:
            if self.app_node.contains_port(disconnected_port_id):
                self.disconnect_app_node()

    def wheelEvent(self, *args, **kwargs):
        """
        Passes through the mouse wheel events to the main window's scroll widget
        """
        if self.hasFocus() and self.scroll_with_strong_focus:
            return QComboBox.wheelEvent(self, *args, **kwargs)
        else:
            return self.scrollWidget.wheelEvent(*args, **kwargs)

    def showPopup(self) -> None:
        """
        Emits the popupAboutToBeShown event, then shows the dropdown menu
        The event is used to refresh the list of items of the dropdown menu before it is shown, to get the most
        up-to-date node information from pipewire

        :return: None
        """
        self.popupAboutToBeShown.emit()
        # print("showing popup!")
        super(ComboBox, self).showPopup()


class RouteWidget(QWidget):
    """
    A RouteWidget contains 0 or more ComboBoxes, the name of the Virtual Sink the Apps that are selected in the
    ComboBoxes are connecting themselves to, a button to add more ComboBoxes (each with a button to remove it
    specifically), and a button to remove the whole RouteWidget

    Creating a new RouteWidget automatically creates a new Virtual Sink through pw_interface, and removing it
    automatically removes the virtual sink

    By default all RouteWidgets crate a single App selection ComboBox, but more and be added and remove on the fly

    Each RouteWidget has its own virtual sink device
    """

    def __init__(self, scrollWidget=None, virtual_sink_manager: pw_interface.VirtualSinkManager = None,
                 node_manager: pw_interface.NodeManager = None, parent_combobox_holder: [[QFrame]] = None):
        """
        Crates a new RouteWidget

        :param scrollWidget: the main window's scrollWidgets to which the scroll events of all child ComboBoxes are passed
        :param virtual_sink_manager: a VirtualSinkManager instance tham keeps track of open virtual sink devices, their creation and closure
        :param node_manager: a NodeManager instance that handles loading the app node list, and connecting / disconnecting the app nodes from the virtual sink
        """
        super().__init__()
        uic.loadUi("ui/RouteWidget.ui",
                   self)  # load the RouteWidget ui from "ui/RouteWidget.ui" created using QT Designer
        self.parent_scrollWidget = scrollWidget
        self.node_manager: pw_interface.NodeManager = node_manager

        self.virtual_sink_manager: pw_interface.VirtualSinkManager = virtual_sink_manager
        # create this routeWidgets own virtual sink
        self.virtual_sink: pw_interface.VirtualSink = self.virtual_sink_manager.create_virtual_sink()
        # set the shown label to the name of the virtual sink
        self.sink_name_label.setText(self.virtual_sink.name)

        # values for adjusting the height of the Combobox Widget's height currently
        self.app_combobox_height: int = 32
        self.app_combobox_vbox_padding: int = 10
        self.routeWidget_min_height = 120

        self.app_output_comboboxes: [QFrame] = []  # keep track of the app comboboxes in this routeWidget
        parent_combobox_holder.append(self.app_output_comboboxes)

        # wire up the buttons
        self.add_more_apps_btn.clicked.connect(self.add_app_output_combobox)
        self.remove_sink_button.clicked.connect(self.remove)

        # get the node of the virtual sink into which the apps are connected in Combobox.on_activated()
        self.output_sink_node: pw_interface.Node = node_manager.get_loopback_node(self.virtual_sink)
        self.output_source_node: pw_interface.Node = node_manager.get_loopback_node(self.virtual_sink, "Source")
        # self.app_nodes: dict[int, pw_interface.Node] = {}

        # add the single default ComboBox
        self.add_app_output_combobox()

        # add target sink combobox
        self.targetSinkComboBox = ComboBox(scrollWidget=self.parent_scrollWidget, node_manager=self.node_manager,
                                           app_node=None, parent_sink_node=self.output_source_node, isAppSourceCB=False)
        self.targetSinkComboBox.popupAboutToBeShown.connect(
            lambda: self.update_app_selection_combobox_items(self.targetSinkComboBox))
        self.targetCBholder.addWidget(self.targetSinkComboBox)

    def update_app_selection_combobox_items(self, cb: ComboBox) -> None:
        """
        Update the list of the Combobox to the most up-to-date apps from pipewire

        :param cb: The ComboBox instance that will have its list updated
        :return: None
        """
        cb.clear()  # remove everything from the list
        self.node_manager.update()  # get the latest app list
        # add the readable node names to the ComboBox's list, as well as a "no app selected" item: " "
        # while excluding nodes that are selected in other comboboxes in the same routeWidget
        cb.addItems([" "] + [f"{node_id}: {node.get_readable_name()}" for node_id, node in
                             sorted(self.node_manager.get_nodes("Source" if cb.isAppSourceCB else "Sink").items(),
                                    key=lambda node: node[1].get_readable_name().lower())
                             if
                             (not cb.isAppSourceCB) or node.id not in [frame.findChild(ComboBox).app_node.id for frame
                                                                       in
                                                                       self.app_output_comboboxes if
                                                                       frame.findChild(ComboBox).app_node is not None]])

    def remove_app_output_combobox(self, cb_frame: QFrame) -> None:
        """
        Remove the combobox and its associated remove button and surrounding QFrame

        :param cb_frame: the QFrame instance which holds the Combobox and remove button
        :return: None
        """
        # find the ComboBox, and disconnect its app's node from the virtual sink
        cb_frame.findChild(ComboBox).disconnect_app_node()
        self.app_output_comboboxes.remove(cb_frame)  # remove the frame
        cb_frame.setParent(None)  # stop displaying it in the RouteWidget

        # set the height of the RouteWidget and the height of the QWidget that holds the QFrames
        self.app_list.setFixedHeight(
            len(self.app_output_comboboxes) * self.app_combobox_height + self.app_combobox_vbox_padding)
        self.setFixedHeight(
            max(len(self.app_output_comboboxes) * self.app_combobox_height + 2 * self.app_combobox_vbox_padding,
                self.routeWidget_min_height))

    def add_app_output_combobox(self) -> None:
        """
        Add a new App selection ComboBox, with its associated remove button and surrounding QFrame

        :return: None
        """

        # Create the QFrame
        hbox: QFrame = QFrame()
        hbox.setContentsMargins(0, 0, 0, 0)

        # Add the frame to the RouteWidget's app_list_vbox, which contains all the QFrames
        self.app_list_vbox.addWidget(hbox, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.app_output_comboboxes.append(hbox)

        # In the QFrame use a QHBoxLayout
        hbox_layout: QHBoxLayout = QHBoxLayout()
        hbox.setLayout(hbox_layout)
        hbox.setFixedHeight(self.app_combobox_height)

        # Create the new ComboBox
        cb: ComboBox = ComboBox(scrollWidget=self.parent_scrollWidget, node_manager=self.node_manager, app_node=None,
                                parent_sink_node=self.output_sink_node)
        cb.setFixedHeight(self.app_combobox_height - 7)
        # connect the popupAboutToBeShown signal to updating the list of the ComboBox
        cb.popupAboutToBeShown.connect(lambda: self.update_app_selection_combobox_items(cb))

        # Create the remove button
        remove_btn: QPushButton = QPushButton("Remove")
        remove_btn.setFixedHeight(self.app_combobox_height - 7)
        remove_btn.setFixedWidth(60)
        remove_btn.clicked.connect(lambda: self.remove_app_output_combobox(hbox))

        # Add the ComboBox adn the remove button the the QFrame's hbox layout
        hbox_layout.addWidget(cb)
        hbox_layout.addWidget(remove_btn)

        # set the height of the RouteWidget and the app_list QWidget to accomodate the new ComboBox
        self.app_list.setFixedHeight(
            len(self.app_output_comboboxes) * self.app_combobox_height + self.app_combobox_vbox_padding)
        self.setFixedHeight(
            max(len(self.app_output_comboboxes) * self.app_combobox_height + 2 * self.app_combobox_vbox_padding,
                self.routeWidget_min_height))

    def remove(self) -> None:
        """
        Remove the RouteWidget
        Removes its virtual sink, then removes itself from the window

        :return: None
        """
        self.virtual_sink_manager.remove(self.virtual_sink)
        self.setParent(None)
