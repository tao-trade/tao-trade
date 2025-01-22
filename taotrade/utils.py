import json
from typing import Any


def write_json(filepath: str, data: Any):
    """
    Write data to a JSON file with proper formatting.

    Args:
        filepath (str): Path to the output JSON file
        data (Any): Data to serialize to JSON format
    """
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)


def read_json(filepath: str) -> Any:
    """
    Read and parse data from a JSON file.

    Args:
        filepath (str): Path to the JSON file to read
    """
    with open(filepath, 'r') as f:
        return json.load(f)
