import json
import shlex
import subprocess


def pw_info_all():
    # all_info_raw: str = subprocess.check_output(shlex.split("/usr/bin/pw-cli info all")).decode("utf-8")
    # print(all_info_raw)

    node_ids = get_object_ids("Node")
    port_ids = get_object_ids("Port")

    print(json.dumps(node_ids, indent=4))
    print(json.dumps(port_ids, indent=4))


def to_python_type(string_input: str):
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


def get_port_info(port_id: int):
    node_port_raw = subprocess.check_output(shlex.split(f"/usr/bin/pw-cli info {port_id}")).decode("utf-8").split("\n")
    port = {}
    for line in node_port_raw:
        if line:
            line_parts = [element.strip('"') for element in line.split()]
            print(line_parts)
            if line.startswith("*"):
                if len(line_parts) > 2:
                    if line_parts[1] == "params:":
                        break
                    if "properties" not in port:
                        port["properties"] = {}
                    port["properties"][line_parts[1]] = to_python_type(line_parts[3])

            else:
                port[line_parts[0]] = to_python_type(line_parts[1])

    print(json.dumps(port, indent=4))


def get_object_ids(object_type: str = "All"):
    object_type = object_type.capitalize()
    accepted_object_types = (
        "Core", "Client", "Module", "Node", "Port", "Link", "Device", "Factory", "Session", "Endpoint", "All")
    if object_type not in accepted_object_types:
        raise ValueError(f"Invalid object type: {object_type}. Must be one of: {accepted_object_types}")

    if object_type == "All":
        object_type = ""
    all_objects_raw = subprocess.check_output(shlex.split("/usr/bin/pw-cli list-objects"))
    obj_ids_raw = subprocess.run(shlex.split(f"rg 'id \d+, type PipeWire:Interface:{object_type}'"),
                                 input=all_objects_raw, stdout=subprocess.PIPE).stdout.decode("utf-8")
    obj_ids = [int(line.split()[1][:-1]) for line in obj_ids_raw.split("\n") if line]
    return obj_ids


def get_port_links() -> [dict[int, dict[str, int]]]:
    info_lines = subprocess.check_output(shlex.split(f"/usr/bin/pw-link --links --id")).decode("utf-8").split("\n")

    links = {}
    port_0_id = None

    for line in info_lines:
        if line:
            if "|->" in line:
                link_id = line.split()[0]
                port_to_id = line.split("|->")[1].split()[0]
                links[link_id] = {"from": port_0_id, "to": port_to_id}

            ## turns out, pw-link --links --id gives the links twice, one in each |->, |<- direction, so it is enough to check then in one direction
            # elif "|<-" in line:
            #     link_id = line.split()[0]
            #     endpoint_from_id = line.split("|<-")[1].split()[0]
            #     links[link_id] = {"from": endpoint_from_id, "to": port_0_id}
            else:
                port_0_id = line.split()[0]

    print(f"{len(links)} connections found")
    return links


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
