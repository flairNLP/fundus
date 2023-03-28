import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from src.library.collection import PublisherCollection
from src.library.collection.base_objects import PublisherEnum

__location__ = os.path.dirname(os.path.realpath(__file__))

de_de = PublisherCollection.de_de


def load_html(publisher_name: str) -> str:
    relative_resource_path = Path(f"./ressources/{publisher_name}.html.gz").resolve()
    absolute_path = os.path.join(__location__, relative_resource_path)

    with open(absolute_path, "rb") as file:
        content = file.read()

    decompressed_content = gzip.decompress(content)
    result = decompressed_content.decode("utf-8")
    return result


def load_data(publisher_name: str) -> Dict[str, Any]:
    relative_resource_path = Path(f"./ressources/{publisher_name}.json").resolve()
    absolute_path = os.path.join(__location__, relative_resource_path)

    with open(absolute_path, "r", encoding="utf-8") as file:
        content = file.read()

    data = json.loads(content)
    if isinstance(data, dict):
        return data
    else:
        raise ValueError("Unknown json format")


@pytest.mark.parametrize(
    "publisher", list(PublisherCollection), ids=[publisher.name for publisher in PublisherCollection]
)
class TestParsing:
    def test_parser(self, publisher: PublisherEnum) -> None:
        html = load_html(publisher.name)
        comparative_data = load_data(publisher.name)
        parser = publisher.parser()

        result = parser.parse(html, "raise")
        for key in comparative_data.keys():
            assert comparative_data[key] == result[key]
