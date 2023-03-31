import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from src.library.collection import PublisherCollection
from src.library.collection.base_objects import PublisherEnum
from tests.resources import attribute_annotation_mapping, parser_test_data_path


def load_html(publisher: PublisherEnum) -> str:
    relative_file_path = Path(f"{publisher.__class__.__name__.lower()}/{publisher.name}.html.gz")
    absolute_path = os.path.join(parser_test_data_path, relative_file_path)

    with open(absolute_path, "rb") as file:
        content = file.read()

    decompressed_content = gzip.decompress(content)
    result = decompressed_content.decode("utf-8")
    return result


def load_data(publisher: PublisherEnum) -> Dict[str, Any]:
    relative_file_path = Path(f"{publisher.__class__.__name__.lower()}/{publisher.name}.json")
    absolute_path = os.path.join(parser_test_data_path, relative_file_path)

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
class TestParser:
    def test_annotations(self, publisher: PublisherEnum) -> None:
        parser = publisher.parser
        for attr in parser.attributes():
            if annotation := attribute_annotation_mapping[attr.__name__]:
                assert (
                    attr.__annotations__.get("return") == annotation
                ), f"Attribute {attr.__name__} for {parser.__name__} failed"

    def test_parsing(self, publisher: PublisherEnum) -> None:
        html = load_html(publisher)
        comparative_data = load_data(publisher)
        parser = publisher.parser()

        result = parser.parse(html, "raise")
        for key in comparative_data.keys():
            assert comparative_data[key] == result[key]
