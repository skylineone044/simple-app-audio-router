import json
import re
import shlex
import subprocess

import time

NODE_APP_NAME_BLACKLIST = ("Plasma PA", "com.github.wwmm.easyeffects",)

NODE_NAME_BLACKLIST = ("Midi-Bridge")


class VirtualSink():
    def __init__(self):
        self.process = subprocess.Popen(shlex.split(
            "/usr/bin/pw-loopback -m '[ FL FR]' --capture-props='media.class=Audio/Sink node.name=test-sink'"))
        self.name = f"loopback-{self.process.pid}-18"
        print(f"Created Virtual Sink: {self.name}")

    def _remove(self) -> None:
        self.process.terminate()
        print(f"Removed Virtual Sink: {self.name}")


class VirtualSinkManager():
    def __init__(self):
        self.virtual_sink_processes: [VirtualSink] = []

    def create_virtual_sink(self) -> VirtualSink:
        vs = VirtualSink()
        self.virtual_sink_processes.append(vs)
        return vs

    def remove(self, vs: VirtualSink) -> None:
        self.virtual_sink_processes.remove(vs)
        vs._remove()

    def terminate_all(self) -> None:
        for proc in self.virtual_sink_processes:
            proc._remove()
        self.virtual_sink_processes = []


class Port():
    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        self.id: int = json_data["id"]
        self.name: str = json_data["properties"]["port.name"]
        self.alias: str = json_data["properties"]["port.alias"]
        self.parent_node_id: int = json_data["properties"]["node.id"]
        self.direction: str = json_data["direction"]

        # self.json_data: dict[str, str | int | dict[str, str | int]] = json_data

    def toJSON(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self) -> str:
        return self.toJSON()


class Node():
    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        self.id: int = json_data["id"]
        self.node_name: str = json_data["properties"]["node.name"] if "node.name" in json_data[
            "properties"] else "Unknown Node"
        self.app_name: str = json_data["properties"]["application.name"] if "application.name" in json_data[
            "properties"] else json_data["properties"]["application.id"] if "application.id" in json_data[
            "properties"] else "Unknown App"
        self.media_name: str = json_data["properties"]["media.name"] if "media.name" in json_data[
            "properties"] else "Unknown Media"
        self.input_ports: [Port] = {}
        self.output_ports: [Port] = {}

        # self.json_data: dict[str, str | int | dict[str, str | int]] = json_data

    def _populate_ports(self, port: Port) -> None:
        if port.parent_node_id == self.id:
            if port.direction == "input":
                self.input_ports[port.id] = port
            elif port.direction == "output":
                self.output_ports[port.id] = port

    def is_source(self) -> bool:
        return len(self.output_ports) > 0

    def is_sink(self) -> bool:
        return len(self.input_ports) > 0

    def get_readable_name(self) -> str:
        return f"{self.node_name}{' (' + self.app_name + ')' if self.node_name != self.app_name else ''}: {self.media_name}"

    def toJSON(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self) -> str:
        return self.toJSON()


class Link():
    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        self.id = json_data["id"]
        self.output_node_id = json_data["output-node-id"]
        self.output_port_id = json_data["output-port-id"]
        self.input_node_id = json_data["input-node-id"]
        self.input_port_id = json_data["input-port-id"]

        # self.json_data = json_data

    def toJSON(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self) -> str:
        return self.toJSON()


def _get_all_data() -> dict[int, str]:
    delim = "\tid: "
    raw_object_data_rjson = dict([(int(item.split("\n")[0]), delim + item) for item in
                                  subprocess.check_output(shlex.split(f"/usr/bin/pw-cli info all")).decode(
                                      "utf-8").split(delim) if item and not item.startswith("remote ")])
    # print(raw_object_data_rjson)
    return raw_object_data_rjson


class NodeManager():
    def __init__(self):
        self.raw_object_data_rjson: dict[int, str] | None = None
        self.ports: dict[int, Port] = {}
        self.nodes: dict[int, Node] = {}
        self.links: dict[int, Link] = {}

        self.update()

    def update(self) -> None:
        self.raw_object_data_rjson = _get_all_data()
        self.ports = {}
        self.nodes = {}
        self.links = {}

        node_start = time.time()
        for node_id in _get_object_ids("Node", self.raw_object_data_rjson):
            node = Node(_get_object_info(node_id, self.raw_object_data_rjson))
            if node.app_name not in NODE_APP_NAME_BLACKLIST and node.node_name not in NODE_NAME_BLACKLIST:
                self.nodes[node_id] = node
        node_end = time.time()
        print(f"parsed {len(self.nodes)} nodes in: {round(node_end - node_start, 4)}s")

        port_start = time.time()
        for port_id in _get_object_ids("Port", self.raw_object_data_rjson):
            self.ports[port_id] = Port(_get_object_info(port_id, self.raw_object_data_rjson))
            try:
                self.nodes[self.ports[port_id].parent_node_id]._populate_ports(self.ports[port_id])
            except KeyError:
                pass  # the ports of blacklisted nodes are not needed
        port_end = time.time()
        print(f"parsed {len(self.ports)} ports in: {round(port_end - port_start, 4)}s")

        links_start = time.time()
        for link_id in _get_object_ids("Link", self.raw_object_data_rjson):
            self.links[link_id] = Link(_get_object_info(link_id, self.raw_object_data_rjson))
        links_end = time.time()
        print(f"parsed {len(self.links)} links in: {round(links_end - links_start, 4)}s")

    def get_nodes(self, direction: str = "All") -> dict[int, Node]:
        direction = direction.capitalize()
        acceptable_directions = ("Source", "Sink", "All")
        if direction not in acceptable_directions:
            raise ValueError(f"Invalid node direction: {direction}. Must be one of: {acceptable_directions}")

        target_nodes = dict([(node_id, node) for node_id, node in self.nodes.items() if
                             direction == "All" or (direction == "Source" and node.is_source()) or (
                                     direction == "Sink" and node.is_sink())])

        return target_nodes

    def get_loopback_sink_node(self, loopback_virtual_sink: VirtualSink) -> Node:
        result_node: Node | None = None
        time_increment: float = 0.02
        counter: int = 0

        while not result_node:
            print(f"Getting sink node for: {loopback_virtual_sink.name}")
            counter += 1
            time.sleep(time_increment * counter)
            self.update()
            for node in self.get_nodes("Sink").values():
                # print("loop ", loopback_virtual_sink.name, "node ", node.media_name)
                if loopback_virtual_sink.name in node.media_name:
                    result_node = node
        print(f"Selected {result_node.get_readable_name()} in {counter} tries")
        return result_node

    def connect_nodes(self, source_node: Node | None, sink_node: Node | None, disconnect=False) -> None:
        if source_node and sink_node:
            print(
                f"{'Dis' if disconnect else ''}connecting node {source_node.id} {source_node.get_readable_name()} {'to' if not disconnect else 'from'} {sink_node.id} {sink_node.get_readable_name()}")
            if len(source_node.output_ports) == len(sink_node.input_ports):
                for source_port_id, sink_port_id in zip(source_node.output_ports, sink_node.input_ports):
                    _pw_link(source_port_id, sink_port_id, disconnect=disconnect)
        else:
            print(
                f"Cannot {'Dis' if disconnect else ''}connect node {source_node} {source_node} {'to' if not disconnect else 'from'} {sink_node.id} {sink_node.get_readable_name()}")

    def disconnect_nodes(self, source_node: Node | None, sink_node: Node | None) -> None:
        self.connect_nodes(source_node, sink_node, disconnect=True)


def to_python_type(string_input: str) -> int | float | str:
    string_input = string_input.strip('"')
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
    if object_data_raw_rjson is None:
        object_data_raw_rjson: dict[int, str] = {
            object_id: subprocess.check_output(shlex.split(f"/usr/bin/pw-cli info {object_id}")).decode("utf-8")}
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
                if not inside_format_section:
                    if line.endswith("format:"):
                        inside_format_section = True
                        continue
                    if not started_properties_section:  # search for the pw_object top level attributes
                        if line.endswith("properties:"):
                            started_properties_section = True
                            inside_format_section = False
                            continue
                        # match pw_object root attributes
                        # match group 1: matches on each line from the beginning to the first ":", but also excluding the
                        # whitespace and any one "*" char at the beginning of the line
                        # match group 2: matches the part between ": " and the end of the line
                        key_value_search = root_attribute_matcher.search(line)
                        pw_object[key_value_search.group(1)] = to_python_type(key_value_search.group(2))

                    else:  # search for the properties of the pw_object
                        if not "properties" in pw_object:
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
                print(f"Unrecognised pattern, skipping: {line}")  # print(e)
    process_end = time.time()
    # print(f"process: {process_end - process_start}")

    return pw_object


def _get_object_ids(object_type: str = "All", object_data_raw_rjson: dict[int, str] = None) -> [int]:
    object_type = object_type.capitalize()
    accepted_object_types = (
        "Core", "Client", "Module", "Node", "Port", "Link", "Device", "Factory", "Session", "Endpoint", "All")
    if object_type not in accepted_object_types:
        raise ValueError(f"Invalid object type: {object_type}. Must be one of: {accepted_object_types}")

    if object_type == "All":
        object_type = ""

    if object_data_raw_rjson is None:
        all_objects_raw = subprocess.check_output(shlex.split("/usr/bin/pw-cli list-objects"))
        obj_ids_raw = subprocess.run(shlex.split(f"rg 'id \d+, type PipeWire:Interface:{object_type}'"),
                                     input=all_objects_raw, stdout=subprocess.PIPE).stdout.decode("utf-8")
        obj_ids = [int(line.split()[1][:-1]) for line in obj_ids_raw.split("\n") if line]
    else:
        obj_ids = []
        for obj_id, obj in object_data_raw_rjson.items():
            lines = obj.split("\n")
            obj_type: str = lines[2].split(":")[3].split("/")[0]
            # print(f"{obj_id=} {obj_type=}")

            if obj_type.capitalize() == object_type:
                obj_ids.append(obj_id)

    return obj_ids


def _pw_link(source_port_id: int, sink_port_id: int, disconnect: bool = False) -> None:
    print(f"{'Dis' if disconnect else ''}connecting ports: {source_port_id}, {sink_port_id}")
    subprocess.run(
        shlex.split(f"/usr/bin/pw-link {'--disconnect' if disconnect else ''} {source_port_id} {sink_port_id}"))
