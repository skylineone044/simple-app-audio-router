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
    info_lines = subprocess.check_output(shlex.split(f"/usr/bin/pw-link --links --id")).decode().split("\n")

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
