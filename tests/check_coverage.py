import json
from pathlib import Path
from typing import Any, Dict, List


def load_json() -> Dict[str, Dict[str, Any]]:
    result = {}
    for file_el in sorted([el for el in Path("./ressources").iterdir() if "json" in el.suffix]):
        with open(file_el, "r", encoding="utf-8") as file:
            result.update({file_el.name: json.load(file)})
    return result


if __name__ == "__main__":
    file_name_dict_dict = load_json()

    required_keys = ["authors", "title", "topics"]

    for key, item in file_name_dict_dict.items():
        for required_key_el in required_keys:
            if required_key_el not in item.keys():
                print(f"{required_key_el} is missing from {key}")
