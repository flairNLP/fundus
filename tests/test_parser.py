import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from src.library.collection import PublisherCollection
from src.library.collection.base_objects import PublisherEnum
from src.parser.html_parser.base_parser import Attribute, BaseParser
from tests.resources import attribute_annotations_mapping, parser_test_data_path


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


class TestBaseParser:
    def test_functions_iter(self, parser_with_function_test, parser_with_static_method):
        assert len(BaseParser.functions()) == 0
        assert len(parser_with_static_method.functions()) == 0
        assert len(parser_with_function_test.functions()) == 1
        assert parser_with_function_test.functions().names == ["test"]

    def test_attributes_iter(self, parser_with_attr_title, parser_with_static_method):
        assert len(BaseParser.attributes()) == 0
        assert len(parser_with_static_method.attributes()) == 0
        assert len(parser_with_attr_title.attributes()) == 1
        assert parser_with_attr_title.attributes().names == ["title"]

    def test_supported_unsupported(self, parser_with_supported_and_unsupported):
        parser = parser_with_supported_and_unsupported
        assert len(parser.attributes()) == 2
        assert parser.attributes().validate == [parser.validate]
        assert parser.attributes().unvalidated == [parser.unvalidated]


@pytest.mark.parametrize(
    "publisher", list(PublisherCollection), ids=[publisher.name for publisher in PublisherCollection]
)
class TestParser:
    def test_annotations(self, publisher: PublisherEnum) -> None:
        parser = publisher.parser
        for attr in parser.attributes().validated:
            if annotation := attribute_annotations_mapping[attr.__name__]:
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
        for attr in attribute_annotations_mapping.keys():
            if value := getattr(parser, attr, None):
                assert isinstance(value, Attribute), f"The name '{attr}' is reserved for attributes only."
