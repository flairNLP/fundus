import json
from pathlib import Path
from typing import Dict, Any

import pytest

from src.library.collection import PublisherCollection
from src.library.collection.base_objects import PublisherEnum
from src.parser.html_parser import BaseParser

de_de = PublisherCollection.de_de


def load_html(publisher_name: str) -> str:
    file_source_path = Path(f"./tests/ressources/{publisher_name}.html").resolve()

    with open(file_source_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content


def load_data(publisher_name: str) -> Dict[str, Any]:
    file_source_path = Path(f"./tests/ressources/{publisher_name}.json").resolve()

    with open(file_source_path, 'r', encoding='utf-8') as file:
        content = file.read()

    return json.loads(content)


@pytest.mark.parametrize(
    "publisher",
    list(PublisherCollection),
    ids=[publisher.name for publisher in PublisherCollection]
)
class TestCrawling:

    def test_parser(self, publisher: PublisherEnum) -> None:
        html = load_html(publisher.name)
        comparative_data = load_data(publisher.name)
        parser = publisher.parser()

        result = parser.parse(html, "raise")
        for key in comparative_data.keys():
            assert comparative_data[key] == result[key]
