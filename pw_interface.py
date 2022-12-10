import json
import re
import shlex
import subprocess
import time

# load config from json config file
with open("config.json", "r") as config_file:
    CONFIG = json.load(config_file)

NODE_APP_NAME_BLACKLIST = CONFIG["NODE_APP_NAME_BLACKLIST"]
NODE_NAME_BLACKLIST = CONFIG["NODE_NAME_BLACKLIST"]


def check_sound_server() -> bool:
    """
    Check what sound server the system is using, and warn the user if it is not pipewire

    :return: True if the detected sound server is pipewire, False otherwise
    """
    pactl_info: str = subprocess.check_output(shlex.split("/usr/bin/pactl info")).decode("utf-8")
    for line in pactl_info.split("\n"):
        if line.startswith("Server Name: "):
            if "PipeWire" in line:
                print("Running on pipwwire")
                return True
            else:
                print(f"Running on {':'.join(line.split(':')[1:])}")
                return False


class VirtualSink():
    """
    A wrapper around a virtual sink subprocess
    """

    def __init__(self):
        """
        Creates a new Virtual Sink using pw-loopback, and keeps it running in the background until it is no longer needed
        """
        self.process = subprocess.Popen(shlex.split(  # creates new virtual sink as a subprocess
            "/usr/bin/pw-loopback -m '[ FL FR]' --capture-props='media.class=Audio/Sink node.name=simple-app-audio-router-virtual-sink'"))
        self.name = f"/usr/bin/pw-loopback-{self.process.pid}"  # the name is always "/usr/bin/pw-loopback-<PID>"
        print(f"Created Virtual Sink: {self.name}")

    def _remove(self) -> None:
        """
        Remove the Virtual sink by terminating the pw-loopback process

        :return: None
        """
        self.process.terminate()
        print(f"Removed Virtual Sink: {self.name}")


class VirtualSinkManager():
    """
    Manages all running virtual sink processes, their creation, and removal
    """

    def __init__(self):
        """
        Crate a new VirtualSinkManager
        It starts with an empty list of Virtual Sinks
        """
        self.virtual_sink_processes: [VirtualSink] = []

    def create_virtual_sink(self) -> VirtualSink:
        """
        Crates a new Virtual sink, and adds it to the list of running processes

        :return: the started VirtualSink instance
        """
        vs = VirtualSink()
        self.virtual_sink_processes.append(vs)
        return vs

    def remove(self, vs: VirtualSink) -> None:
        """
        Removes the VirtualSink instance by stopping its process, and removing it form the list of running processes

        :param vs: the VirtualSink instance to be stopped and removed
        :return: None
        """
        self.virtual_sink_processes.remove(vs)
        vs._remove()

    def terminate_all(self) -> None:
        """
        Termiante all running virtual sink processes

        :return: None
        """
        for proc in self.virtual_sink_processes:
            proc._remove()
        self.virtual_sink_processes = []


class Port():
    """
    wrapper class around pipwwire's port object
    """

    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        """
        Create a new port object, and keep only the needed information

        :param json_data: the information of the port object in json form parsed by _get_object_info()
        """
        self.id: int = json_data["id"]
        self.name: str = json_data["properties"]["port.name"]
        self.alias: str = json_data["properties"]["port.alias"]
        self.parent_node_id: int = json_data["properties"]["node.id"]
        self.direction: str = json_data["direction"]

        # self.json_data: dict[str, str | int | dict[str, str | int]] = json_data

    def toJSON(self) -> str:
        """
        Convert all attributes to json form

        :return: the string of this object in json form
        """
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self) -> str:
        """
        Convert this port object to a string

        :return: all attributes in json form
        """
        return self.toJSON()

    def __repr__(self):
        return str(self)


class Node():
    """

    wrapper class around pipwwire's node object
    """

    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        """
        Create a new node object, and keep only the needed information

        :param json_data: the information of the node object in json form parsed by _get_object_info()
        """
        self.id: int = json_data["id"]

        # not all nodes have the same properties, so app_name some have multiple options for a value
        # node.name preference order: node.name, "Unknown Node"
        # app.name preference order: application.name, application.id, "Unknown Node"
        # media.name preference order: media.name, "Unknown Media"
        self.node_name: str = json_data["properties"]["node.name"] if "node.name" in json_data[
            "properties"] else "Unknown Node"
        self.app_name: str = json_data["properties"]["application.name"] if "application.name" in json_data[
            "properties"] else json_data["properties"]["application.id"] if "application.id" in json_data[
            "properties"] else "Unknown App"
        self.media_name: str = json_data["properties"]["media.name"] if "media.name" in json_data[
            "properties"] else "Unknown Media"

        # List of Port objects that are in this node
        self.input_ports: [Port] = {}
        self.output_ports: [Port] = {}

        # self.json_data: dict[str, str | int | dict[str, str | int]] = json_data

    def _populate_ports(self, port: Port) -> None:
        """
        Populates the given port object into the correct (input / output) sides of this node
        :param port: the port to be inserted

        :return: None
        """
        if port.parent_node_id == self.id:
            if port.direction == "input":
                self.input_ports[port.id] = port
            elif port.direction == "output":
                self.output_ports[port.id] = port

    def contains_port(self, port_id: int) -> bool:
        """
        Determine if this node contains a port with certain id or not

        :param port_id: the port id which is searched for
        :return: True if this node has any port if the port id given in the parameter
        """
        return port_id in self.input_ports.keys() or port_id in self.output_ports.keys()

    def is_source(self) -> bool:
        """
        Determines if this node is a source node or not.
        A source node is a node which has 1 or more output ports

        :return: True if this node is a source node, False otherwise
        """
        return len(self.output_ports) > 0

    def is_sink(self) -> bool:
        """
        Determines if this node is a sink node or not.
        A sink node is a node which has 1 or more input ports

        :return: True if this node is a sink node, False otherwise
        """
        return len(self.input_ports) > 0

    def get_readable_name(self) -> str:
        """
        Generates a more easily human readable name for this node by composing several attributes
        format:
            if node_name and app_name are the same:
                "{node_name}: {media_name}"
                for example: Firefox: AudioStream
            if node_name and app_name are different:
                "{node_name} ({app_name}): {media_name}"
                for example: PipeWire ALSA [VirtualBoxVM] (VirtualBoxVM): ALSA Playback

        :return: The human-readable string name
        """
        return f"{self.node_name}{' (' + self.app_name + ')' if self.node_name != self.app_name else ''}: {self.media_name}"

    def toJSON(self) -> str:
        """
        Convert all attributes to json form

        :return: the string of this object in json form
        """
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self) -> str:
        """
        Convert this node object to a string

        :return: all attributes in json form
        """
        return self.toJSON()

    def __repr__(self):
        return str(self)


class Link():
    """
    wrapper class around pipwwire's link object
    """

    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        """
        Create a new link object, and keep only the needed information

        :param json_data: the information of the link object in json form parsed by _get_object_info()
        """
        self.id = json_data["id"]
        self.output_node_id = json_data["output-node-id"]
        self.output_port_id = json_data["output-port-id"]
        self.input_node_id = json_data["input-node-id"]
        self.input_port_id = json_data["input-port-id"]

        # self.json_data = json_data

    def toJSON(self) -> str:
        """
        Convert all attributes to json form

        :return: the string of this object in json form
        """
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self) -> str:
        """
        Convert this link object to a string

        :return: all attributes in json form
        """
        return self.toJSON()

    def __repr__(self):
        return str(self)


def _get_all_data() -> dict[int, str]:
    """
    Gets the information of all pipewire objects using "pw-cli info all", and slices it up to be a list of strings,
    where each string contains the information of a single pipewire object

    :return: python dict containing int - string paris, where the int is the pipewire id or the object,
    and the string is the information about that object
    """
    delim = "\tid: "
    while True:
        try:
            data = subprocess.check_output(shlex.split(f"/usr/bin/pw-cli info all"))
            break
        except subprocess.CalledProcessError as cpe:
            print(f"An Error occurred while fetching the data {cpe.returncode}")
            time.sleep(0.02)
            continue
    raw_object_data_rjson = dict(
        [(int(item.split("\n")[0]), delim + item) for item in data.decode("utf-8").split(delim) if
         item and not item.startswith("remote ")])
    # print(raw_object_data_rjson)
    return raw_object_data_rjson


class NodeManager():
    """
    Manages and stores the loaded pipewire objects: Nodes, Ports, and Links
    """

    def __init__(self):
        """
        Create a new NodeManager instance: initialize the dicts in which the pipewire objects are stored
        """
        self.raw_object_data_rjson: dict[int, str] | None = None
        self.ports: dict[int, Port] = {}
        self.nodes: dict[int, Node] = {}
        self.links: dict[int, Link] = {}

        self.update()

    def update(self) -> None:
        """
        load in the pipwwire objects from _get_all_date() into the dicts

        :return: None
        """
        self.raw_object_data_rjson = _get_all_data()
        self.ports = {}
        self.nodes = {}
        self.links = {}

        # load the nodes
        node_start = time.time()
        for node_id in _get_object_ids("Node", self.raw_object_data_rjson):
            node = Node(_get_object_info(node_id, self.raw_object_data_rjson))
            # some app and node names are blacklisted, as they are not useful to be connected to an output port, and
            # they just clog up the dropdown menu
            if node.app_name not in NODE_APP_NAME_BLACKLIST and node.node_name not in NODE_NAME_BLACKLIST:
                self.nodes[node_id] = node
        node_end = time.time()
        print(f"parsed {len(self.nodes)} nodes in: {round(node_end - node_start, 4)}s")

        # load the ports
        port_start = time.time()
        for port_id in _get_object_ids("Port", self.raw_object_data_rjson):
            self.ports[port_id] = Port(_get_object_info(port_id, self.raw_object_data_rjson))
            try:
                self.nodes[self.ports[port_id].parent_node_id]._populate_ports(self.ports[port_id])
            except KeyError:
                pass  # the ports of blacklisted nodes are not needed
        port_end = time.time()
        print(f"parsed {len(self.ports)} ports in: {round(port_end - port_start, 4)}s")

        # load the links
        links_start = time.time()
        for link_id in _get_object_ids("Link", self.raw_object_data_rjson):
            self.links[link_id] = Link(_get_object_info(link_id, self.raw_object_data_rjson))
        links_end = time.time()
        print(f"parsed {len(self.links)} links in: {round(links_end - links_start, 4)}s")

    def get_nodes(self, direction: str = "All") -> dict[int, Node]:
        """
        Get nodes of a certain type: Sink, Source, or all of them

        :param direction: the type of nodes to return: can be "Source", "Sink", "All"
        :return: a dict containing int - node pairs or the desired type
        """
        # handle incorrect type string
        direction = direction.capitalize()
        acceptable_directions = ("Source", "Sink", "All")
        if direction not in acceptable_directions:
            raise ValueError(f"Invalid node direction: {direction}. Must be one of: {acceptable_directions}")

        # get the correct (node_id, node) pairs into a dict
        target_nodes = dict([(node_id, node) for node_id, node in self.nodes.items() if
                             direction == "All" or (direction == "Source" and node.is_source()) or (
                                     direction == "Sink" and node.is_sink())])

        return target_nodes

    def get_loopback_node(self, loopback_virtual_sink: VirtualSink, node_type="Sink") -> Node:
        """
        get the sink node of the desired virtual sink

        :param loopback_virtual_sink: A VirtualSink instance for getting the corresponding sink node
        :return: a Node object that corresponds to the VirtualSink given in the parameter
        """
        allowed_types = ("Sink", "Source", "Monitor")
        if node_type not in allowed_types:
            raise ValueError(f"Invalid argument: {node_type} Must be one of: {allowed_types}")
        # retry until the node is found, because piprwire does not always refresh the data quickly enough between
        # creating the loopback device and the calling of this function
        result_node: Node | None = None
        time_increment: float = 0.02
        counter: int = 0
        max_retries = 20

        while not result_node and counter < max_retries:
            print(f"Getting sink node for: {loopback_virtual_sink.name}")
            counter += 1
            time.sleep(time_increment * counter)  # wait for pipewire to refresh the data
            self.update()  # request and load the data
            for node in self.get_nodes(node_type).values():  # search for the correct Sink node
                # print("loop ", loopback_virtual_sink.name, "node ", node.media_name)
                if loopback_virtual_sink.name in node.media_name:
                    result_node = node

        if counter >= max_retries:
            print(f"Could not find loopback {node_type} node")
            raise RuntimeError(f"Could not find loopback {node_type} node")

        print(f"Selected {result_node.get_readable_name()} in {counter} tries")

        # by default the output of the virtual loopback device is connected to the system audio output, thus anything
        # connected to the input of the loopback device gets heard twice, in quick succession making it sound louder
        # due to the low latency, but this behaviour is not desired, so dircennecting the loopback device from
        # the system output:
        self.disconnect_loopback_output(loopback_virtual_sink)

        return result_node

    def disconnect_loopback_output(self, loopback_virtual_sink: VirtualSink) -> None:
        """
        Disconnect the loopback device output form the system output

        :param loopback_virtual_sink: the loopback device for which the loopback output is to be disconnected
        :return: None
        """
        # by default the loopback output node is connected to the system output

        print("disconnecting virtual sink output...")
        result_node: Node | None = None
        time_increment: float = 0.02
        counter: int = 0

        # retry until the node is found, because piprwire does not always refresh the data quickly enough between
        # creating the loopback device and the calling of this function
        while not result_node:
            print(f"getting source output node for: {loopback_virtual_sink.name}")
            counter += 1
            time.sleep(time_increment * counter)  # wait for pipewire to refresh the data
            self.update()  # request and load the data
            for node in self.get_nodes("Source").values():  # search for the correct Source node
                # print("loop ", loopback_virtual_sink.name, "node ", node.media_name)
                if f"{loopback_virtual_sink.name} output" == node.media_name:
                    # print(node)
                    result_node = node

        print(f"Selected {result_node.get_readable_name()} in {counter} tries")

        # disconnect all outgoing links from this node
        self.disconnect_all_links_from_ports((result_node.output_ports.keys()))

    def disconnect_all_links_from_ports(self, target_port_ids: [int]) -> None:
        """
        Disconnect all links that go to or from a port

        :param target_port_ids: A list of port IDs
        :return: None
        """
        for link_id, link in self.links.items():  # go through all links
            # if target port is in link
            if link.output_port_id in target_port_ids or link.input_port_id in target_port_ids:
                _pw_link(link_id=link_id, disconnect=True)  # disconnect the link


def connect_nodes(source_node: Node | None, sink_node: Node | None, disconnect=False, reverse_order=False) -> bool:
    """
    Connect or disconnect the ports of two nodes, if the number of their ports match

    :param reverse_order: whether to reverse the order of the two input nodes
    :param source_node: Node the links go from
    :param sink_node: Node the links go to
    :param disconnect: if true the nodes will be disconnected, else connected, default: False
    :return: True if the nodes could be connected / disconnected, False otherwise
    """
    if reverse_order:
        source_node, sink_node = sink_node, source_node

    if source_node and sink_node:  # if both nodes exist and not None
        print(
            f"{'Dis' if disconnect else ''}connecting node {source_node.id} {source_node.get_readable_name()} {'to' if not disconnect else 'from'} {sink_node.id} {sink_node.get_readable_name()}")
        if len(source_node.output_ports) == len(sink_node.input_ports):  # if number of ports match
            # link / unlink the corresponding ports
            for source_port_id, sink_port_id in zip(
                    # get the IDs of the ports, but sort them based on the flipped version of their name attribute
                    # the name attribute is commonly output_FL, output_FR, playback_FL, playback_FR
                    # sorting based on the reverse of them ensures _FL - _FL and _FR - _FR pairs remain together
                    [port.id for port in sorted(source_node.output_ports.values(), key=lambda item: item.name[::-1])],
                    [port.id for port in sorted(sink_node.input_ports.values(), key=lambda item: item.name[::-1])]):
                _pw_link(source_port_id=source_port_id, sink_port_id=sink_port_id, disconnect=disconnect)
            return True
        else:
            print(
                f"Cannot {'Dis' if disconnect else ''}connect node {source_node} {'to' if not disconnect else 'from'} {sink_node.id} {sink_node.get_readable_name()}: Their port numbers do not match: {len(source_node.output_ports)} : {len(sink_node.input_ports)}")
            return False
    else:
        print(
            f"Cannot {'Dis' if disconnect else ''}connect node {source_node} {'to' if not disconnect else 'from'} {sink_node.id} {sink_node.get_readable_name()}")
        return False


def connect_nodes_replace_connection(source_node: Node | None, sink_node: Node | None, node_manager: NodeManager,
                                     reverse_order=False, replace_connection=False) -> bool:
    """
    Connect two nodes, while disconnecting all connections going to the input of the sink node
    :param source_node: the node with the outputs ports
    :param sink_node: the node which will have all its connections removed, and replaced with connections to the source node
    :param node_manager: a NodeManager instance storing the Links
    :param reverse_order: whether to reverse the order of the two nodes
    :param replace_connection: whether to actually replace the connections, or just behave like the connect_nodes function
    :return:
    """
    if reverse_order:
        source_node, sink_node = sink_node, source_node

    if replace_connection:
        disconnect_all_inputs(sink_node, node_manager=node_manager)
    return connect_nodes(source_node, sink_node)


def disconnect_all_inputs(node: Node, node_manager: NodeManager):
    """
    Disconnect all links from a node's input side
    :param node: node which will have its inputs disconnected
    :param node_manager: a NodeManager instance storing all the links
    """
    print(f"Disconnecting all inputs from: {node}")
    for link_id, link in node_manager.links.items():
        # print(f"link: {link}")
        if link.input_port_id in node.input_ports.keys():
            print(f"removing link: {link}")
            _pw_link(link.output_port_id, link.input_port_id, disconnect=True)


def disconnect_nodes(source_node: Node | None, sink_node: Node | None) -> None:
    """
    Disconnect or the ports of two nodes, if the number of their ports match

    :param source_node: Node the links go from
    :param sink_node: Node the links go to
    :return: None
    """
    connect_nodes(source_node, sink_node, disconnect=True)


def to_python_type(string_input: str) -> bool | int | float | str:
    """
    Convert a string literal to a native python type if possible

    :param string_input: the string literal to be converted
    :return: native python value of type: bool, int, float, or str
    """
    # ger rid of extra '"' first: "\"text\"" -> "text"
    string_input = string_input.strip('"')

    # try to convert the value
    # order of types to try:
    # bool, int, float, str
    if string_input == "true":
        return True
    elif string_input == "false":
        return False
    else:
        try:
            int(string_input)
            return int(string_input)
        except ValueError:
            try:
                float(string_input)
                return float(string_input)
            except ValueError:
                return string_input


def _get_object_info(object_id: int, object_data_raw_rjson: dict[int, str] = None) -> dict[
    str, str | int | dict[str, str | int]]:
    """
    Parse a section of the string given by _get_all_data() that contains information about a single pipewire object
    into a python dict

    Only the top level attributes and properties are parsed, any other sections such
    as format, Params, or others are ignored

    :param object_id: the id of the pipewire object
    :param object_data_raw_rjson: the string containing the data about a single object only, returned from pw-cli
    :return: a dict containing the objects' top level attributes and properties
    """

    # if the object data is not given in the argument, request it from pw-cli
    if object_data_raw_rjson is None:
        object_data_raw_rjson: dict[int, str] = {
            object_id: subprocess.check_output(shlex.split(f"/usr/bin/pw-cli info {object_id}")).decode("utf-8")}

    # parsing is done line-by-line
    # each line can match one of 2 regular expressions:
    #
    # one for the toplevel attributes:
    #   for example: *      output ports: 2/65
    #                ^1~~~~ ^2~~~~~~~~~~  ^3~~
    #   where 1: leading whitespace and the optional "*" char is ignored
    #         2: the attribute key
    #         3: the attribute value
    #
    # and one for properties:
    #   for example: *		application.name = "Tauon Music Box"
    #                ^1~~~~ ^2~~~~~~~~~~~~~~   ^3~~~~~~~~~~~~~~~
    #   where 1: leading whitespace and the optional "*" char is ignored
    #         2: the property key
    #         3: the property value
    pw_object = {}
    started_properties_section = False
    inside_format_section = False

    root_attribute_matcher = re.compile("^(?:\**\s+)([a-zA-Z0-9 \.\-\_]+)(?:: )(.+$)")
    property_matcher = re.compile("^(?:\**\s+)([a-zA-Z0-9\.\-\_]+)(?: = )(.+$)")

    process_start = time.time()
    for line in object_data_raw_rjson[object_id].split("\n"):
        if line:
            try:
                if "params: " in line:  # ignore pw_object params, I do not need them
                    break
                if not inside_format_section:  # ignore the format section (it is found in links)
                    if line.endswith("format:"):
                        inside_format_section = True
                        continue
                    if not started_properties_section:  # search for the pw_object top level attributes
                        if line.endswith("properties:"):
                            started_properties_section = True
                            inside_format_section = False
                            continue
                        # match pw_object toplevel attributes
                        # match group 1: matches on each line from the beginning to the first ":", but also excluding the
                        # whitespace and any one "*" char at the beginning of the line
                        # match group 2: matches the part between ": " and the end of the line
                        key_value_search = root_attribute_matcher.search(line)
                        pw_object[key_value_search.group(1)] = to_python_type(key_value_search.group(2))

                    else:  # search for the properties of the pw_object
                        if "properties" not in pw_object:
                            pw_object["properties"] = {}
                        # match pw_object properties
                        # match group 1: matches on each line from the beginning to the first " = " while excluding the "*"
                        # and whitespace at the beginning
                        # match group 2: matches the part between " = " and the end of the line
                        key_value_search = property_matcher.search(line)
                        pw_object["properties"][key_value_search.group(1)] = to_python_type(key_value_search.group(2))
                else:
                    if line.endswith("properties:"):
                        started_properties_section = True
                        inside_format_section = False
                        continue
            except Exception as e:
                print(f"Unrecognised pattern, skipping: {line}")
    process_end = time.time()
    # print(f"process: {process_end - process_start}")

    return pw_object


def _get_object_ids(object_type: str = "All", object_data_raw_rjson: dict[int, str] = None) -> [int]:
    """
    Get the pipewire object IDs of certain types of objects

    :param object_type: the type of the desired objects: one of "Core", "Client", "Module", "Node", "Port", "Link",
                                                                "Device", "Factory", "Session", "Endpoint", "All"
    :param object_data_raw_rjson: a dict of int - str pairs where the int is an object id, and the str is the string
                                  containing the data of a piprwire object, as loaded by _get_all_data()
    :return: the list of the IDs of all objects of the desired type
    """
    object_type = object_type.capitalize()
    accepted_object_types = (
        "Core", "Client", "Module", "Node", "Port", "Link", "Device", "Factory", "Session", "Endpoint", "All")
    if object_type not in accepted_object_types:
        raise ValueError(f"Invalid object type: {object_type}. Must be one of: {accepted_object_types}")

    if object_type == "All":
        object_type = ""

    if object_data_raw_rjson is None:  # if the object data is not given in the argument, request it from pw-cli
        all_objects_raw = subprocess.check_output(shlex.split("/usr/bin/pw-cli list-objects"))
        obj_ids_raw = subprocess.run(shlex.split(f"rg 'id \d+, type PipeWire:Interface:{object_type}'"),
                                     input=all_objects_raw, stdout=subprocess.PIPE).stdout.decode("utf-8")
        obj_ids = [int(line.split()[1][:-1]) for line in obj_ids_raw.split("\n") if line]
    else:  # if object data is given
        obj_ids = []
        for obj_id, obj in object_data_raw_rjson.items():  # go through all object strings
            lines = obj.split("\n")
            # the second line contains the object type:
            # for example: type: PipeWire:Interface:Node/3
            #                                       ^~~~
            obj_type: str = lines[2].split(":")[3].split("/")[0]
            # print(f"{obj_id=} {obj_type=}")

            if obj_type.capitalize() == object_type:  # if it is of the correct type, add it to the result list
                obj_ids.append(obj_id)

    return obj_ids


def _pw_link(source_port_id: int | None = None, sink_port_id: int | None = None, link_id: int | None = None,
             disconnect: bool = False) -> None:
    """
    Create or remove a link between two ports using pw-link

    2 main ways to call this function:
        1: _pw_link(source_port_id, sink_port_id [disconnect=True])  -> the ports will be connected / disconnected
        2: _pw_link(link_id, disconnect=True) -> the link will be removed

    :param source_port_id: a port on the output side of a node
    :param sink_port_id: a port on the input side of a node
    :param link_id: a link id
    :param disconnect: if true the ports wiil be disconnected / the link will be removed, if false, the ports will be connected.
    :return: None
    """
    if source_port_id is not None and sink_port_id is not None and link_id is None:
        print(f"{'Dis' if disconnect else ''}connecting ports: {source_port_id}, {sink_port_id}")
        subprocess.run(
            shlex.split(f"/usr/bin/pw-link {'--disconnect' if disconnect else ''} {source_port_id} {sink_port_id}"))
    elif source_port_id is None and sink_port_id is None and link_id is not None and disconnect:
        print(f"Disconnecting link: {link_id}")
        subprocess.run(shlex.split(f"/usr/bin/pw-link --disconnect {link_id}"))
