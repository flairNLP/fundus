import datetime
import gzip
import json
import os
from json import JSONDecoder
from pathlib import Path
from typing import Any, Callable, Dict

import pytest

from src.library.collection import PublisherCollection
from src.library.collection.base_objects import PublisherEnum
from src.parser.html_parser.base_parser import Attribute
from tests.resources import attribute_annotation_mapping, parser_test_data_path


class CustomJsonDecoder(JSONDecoder):
    # The lambda in the signature is used to satisfy mypy
    def decode(self, s: str, _w: Callable[..., Any] = lambda x: x) -> Any:
        transformations: Dict[str, Callable[..., Any]] = {
            "publishing_date": lambda x: datetime.datetime.fromisoformat(x)
        }

        raw_data = json.loads(s)
        transformed_dict = {}
        for key_el in raw_data:
            transformation = transformations.get(key_el, lambda x: x)
            transformed_dict.update({key_el: transformation(raw_data[key_el])})

        return transformed_dict


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

    data = json.loads(content, cls=CustomJsonDecoder)
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
            if annotation := attribute_annotation_mapping.get(attr.__name__):
                assert (
                    attr.__annotations__.get("return") == annotation
                ), f"Attribute {attr.__name__} for {parser.__name__} failed"
            else:
                raise KeyError(f"Unsupported attribute '{attr.__name__}'")

    def test_parsing(self, publisher: PublisherEnum) -> None:
        html = load_html(publisher)
        comparative_data = load_data(publisher)
        parser = publisher.parser()

        # enforce test coverage
        attrs_required_to_cover = {"title", "authors", "topics"}
        supported_attrs = set(parser.attributes().names)
        missing_attrs = attrs_required_to_cover & supported_attrs - set(comparative_data.keys())
        assert not missing_attrs, f"Test JSON does not cover the following attribute(s): {missing_attrs}"

        # compare data
        result = parser.parse(html, "raise")
        for key in comparative_data.keys():
            assert comparative_data[key] == result[key]

    def test_reserved_attribute_names(self, publisher: PublisherEnum):
        parser = publisher.parser
        for attr in attribute_annotation_mapping.keys():
            if value := getattr(parser, attr, None):
                assert isinstance(value, Attribute), f"The name '{attr}' is reserved for attributes only."
