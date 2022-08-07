import os
import subprocess

def get_node_info(node_info_type: str) -> [dict[int, str]]:
    valid_node_info_types = ("input", "output", "links")
    if node_info_type not in valid_node_info_types:
        raise ValueError(f"Invalid node_info_type '{node_info_type}': must be one of {valid_node_info_types}")

    info_lines = subprocess.check_output(["pw-link", f"--{node_info_type}", "--id"]).decode().split("\n")
    node_outputs = [
        {
            "id": int(line.split()[0]),
            "name": " ".join(line.split()[1:])
         }
        for line in info_lines if line
    ]
    return node_outputs

def get_node_inputs() -> [dict[int, str]]:
    return get_node_info("input")

def get_node_outputs() -> [dict[int, str]]:
    return get_node_info("output")

def get_node_links() -> [dict[int, str]]:
    return get_node_info("links")
