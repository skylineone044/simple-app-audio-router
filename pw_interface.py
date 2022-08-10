import json
import re
import shlex
import subprocess

import time


class Port():
    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        self.id: int = json_data["id"]
        self.name: str = json_data["properties"]["port.name"]
        self.alias: str = json_data["properties"]["port.alias"]
        self.parent_node_id: int = json_data["properties"]["node.id"]
        self.direction: str = json_data["direction"]

        # self.json_data: dict[str, str | int | dict[str, str | int]] = json_data

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
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

    def _populate_ports(self, port: Port):
        if port.parent_node_id == self.id:
            if port.direction == "input":
                self.input_ports[port.id] = port
            elif port.direction == "output":
                self.output_ports[port.id] = port

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
        return self.toJSON()


class Link():
    def __init__(self, json_data: dict[str, str | int | dict[str, str | int]]):
        self.id = json_data["id"]
        self.output_node_id = json_data["output-node-id"]
        self.output_port_id = json_data["output-port-id"]
        self.input_node_id = json_data["input-node-id"]
        self.input_port_id = json_data["input-port-id"]

        # self.json_data = json_data

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
        return self.toJSON()


def get_all_data():
    delim = "\tid: "
    raw_object_data_rjson = dict([(int(item.split("\n")[0]), delim + item) for item in
                                  subprocess.check_output(shlex.split(f"/usr/bin/pw-cli info all")).decode(
                                      "utf-8").split(delim) if item])
    # print(raw_object_data_rjson)
    return raw_object_data_rjson


class NodeManager():
    def __init__(self):
        self.raw_object_data_rjson = get_all_data()
        # print(self.raw_object_data_rjson)
        self.ports: dict[int, Port] = {}
        self.nodes: dict[int, Node] = {}
        self.links: dict[int, Link] = {}

        self.update()

    def update(self):
        self.ports = {}
        self.nodes = {}
        self.links = {}

        node_start = time.time()
        for node_id in get_object_ids("Node", self.raw_object_data_rjson):
            self.nodes[node_id] = Node(get_object_info(node_id, self.raw_object_data_rjson))
        node_end = time.time()
        print(f"node itme: {node_end - node_start}")

        port_start = time.time()
        for port_id in get_object_ids("Port", self.raw_object_data_rjson):
            self.ports[port_id] = Port(get_object_info(port_id, self.raw_object_data_rjson))
            self.nodes[self.ports[port_id].parent_node_id]._populate_ports(self.ports[port_id])
        port_end = time.time()
        print(f"port itme: {port_end - port_start}")

        links_start = time.time()
        for link_id in get_object_ids("Link", self.raw_object_data_rjson):
            self.links[link_id] = Link(get_object_info(link_id, self.raw_object_data_rjson))
        links_end = time.time()
        print(f"links itme: {links_end - links_start}")


def to_python_type(string_input: str):
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


def get_object_info(object_id: int, object_data_raw_rjson: dict[int, str] = None):
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


def get_object_ids(object_type: str = "All", object_data_raw_rjson: dict[int, str] = None):
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


class VirtualSink():
    def __init__(self):
        self.process = subprocess.Popen(shlex.split(
            "/usr/bin/pw-loopback -m '[ FL FR]' --capture-props='media.class=Audio/Sink node.name=test-sink'"))
        self.name = f"loopback-{self.process.pid}-18"
        print(f"Created Virtual Sink: {self.name}")

    def _remove(self):
        self.process.terminate()
        print(f"Removed Virtual Sink: {self.name}")


class VirtualSinkManager():
    def __init__(self):
        self.virtual_sink_processes: [VirtualSink] = []

    def create_virtual_sink(self):
        vs = VirtualSink()
        self.virtual_sink_processes.append(vs)
        return vs

    def remove(self, vs: VirtualSink):
        self.virtual_sink_processes.remove(vs)
        vs._remove()

    def terminate_all(self):
        for proc in self.virtual_sink_processes:
            proc._remove()
        self.virtual_sink_processes = []
