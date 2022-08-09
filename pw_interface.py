import subprocess
import shlex


def get_node_info(node_info_type: str) -> dict[int, str]:
    valid_node_info_types = ("input", "output")
    if node_info_type not in valid_node_info_types:
        raise ValueError(f"Invalid node_info_type '{node_info_type}': must be one of {valid_node_info_types}")

    info_lines = subprocess.check_output(shlex.split(f"/usr/bin/pw-link --{node_info_type} --id")).decode().split("\n")

    node_connections = {}
    for line in info_lines:
        if line:
            node_connections[int(line.split()[0])] = " ".join(line.split()[1:])

    print(f"{len(node_connections)} {node_info_type}s found")
    return node_connections


def get_node_inputs() -> [dict[int, str]]:
    return get_node_info("input")


def get_node_outputs() -> [dict[int, str]]:
    return get_node_info("output")


def get_node_links() -> [dict[int, dict[str, int]]]:
    info_lines = subprocess.check_output(shlex.split(f"/usr/bin/pw-link --links --id")).decode().split("\n")

    node_connections = {}
    endpoint0_id = None

    for line in info_lines:
        if line:
            if "|->" in line:
                conn_id = line.split()[0]
                endpoint_to_id = line.split("|->")[1].split()[0]
                node_connections[conn_id] = {"from": endpoint0_id, "to": endpoint_to_id}

            ## turns out, pw-link --links --id gives the links twice, one in each |->, |<- direction, so it is enough to check then in one direction
            # elif "|<-" in line:
            #     conn_id = line.split()[0]
            #     endpoint_from_id = line.split("|<-")[1].split()[0]
            #     node_connections[conn_id] = {"from": endpoint_from_id, "to": endpoint0_id}
            else:
                endpoint0_id = line.split()[0]

    print(f"{len(node_connections)} connections found")
    return node_connections


class VirtualSink():
    def __init__(self):
        self.process = subprocess.Popen(
            shlex.split(
                "/usr/bin/pw-loopback -m '[ FL FR]' --capture-props='media.class=Audio/Sink node.name=test-sink'"))
        self.name = f"loopback-{self.process.pid}-18"
        print(f"Created Virtual Sink: {self.name}")

    def remove(self):
        self.process.terminate()
        print(f"Removed Virtual Sink: {self.name}")
