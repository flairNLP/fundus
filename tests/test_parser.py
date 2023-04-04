import gzip
import json
import os
from os.path import exists
from pathlib import Path
from typing import Any, Dict, List

import lxml.html
import pytest

from doc import docs_path
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


class TestParser:
    def test_supported(self):
        relative_path = Path("supported_news.md")
        supported_news_path = os.path.join(docs_path, relative_path)

        if not exists(supported_news_path):
            raise FileNotFoundError(f"The '{relative_path}' is missing. Run 'python -m src/utils/tables.py'")

        with open(supported_news_path, "rb") as file:
            content = file.read()

        root = lxml.html.fromstring(content)
        parsed_names: List[lxml.html.HtmlElement] = root.xpath("//table[contains(@class,'source')]//code/text()")
        for publisher in PublisherCollection:
            assert publisher.name in parsed_names, (
                f"Publisher {publisher.name} is not included in README.md. " f"Run 'python -m src/utils/table.py'"
            )

    @pytest.mark.parametrize(
        "publisher", list(PublisherCollection), ids=[publisher.name for publisher in PublisherCollection]
    )
    def test_annotations(self, publisher: PublisherEnum) -> None:
        parser = publisher.parser
        for attr in parser.attributes():
            if annotation := attribute_annotation_mapping[attr.__name__]:
                assert (
                    attr.__annotations__.get("return") == annotation
                ), f"Attribute {attr.__name__} for {parser.__name__} failed"

    @pytest.mark.parametrize(
        "publisher", list(PublisherCollection), ids=[publisher.name for publisher in PublisherCollection]
    )
    def test_parsing(self, publisher: PublisherEnum) -> None:
        html = load_html(publisher)
        comparative_data = load_data(publisher)
        parser = publisher.parser()

        result = parser.parse(html, "raise")
        for key in comparative_data.keys():
            assert comparative_data[key] == result[key]
