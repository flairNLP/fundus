import json
from pathlib import Path
from typing import Dict, Any

import pytest

from src.library.collection import PublisherCollection
from src.parser.html_parser import BaseParser

de_de = PublisherCollection.de_de


def load_html(parser: BaseParser) -> str:
    name = parser.__class__.__name__
    file_source_path = Path(f"./tests/ressources/{name}.html").resolve()

    with open(file_source_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content


def load_data(parser: BaseParser) -> Dict[str, Any]:
    name = parser.__class__.__name__
    file_source_path = Path(f"./tests/ressources/{name}.json").resolve()

    with open(file_source_path, 'r', encoding='utf-8') as file:
        content = file.read()

    return json.loads(content)


@pytest.mark.parametrize(
    "parser", [publisher.parser() for publisher in de_de], ids=[publisher.name for publisher in de_de]
)
class TestCrawling:

    def test_parser(self, parser: BaseParser) -> None:
        html = load_html(parser)
        comparative_data = load_data(parser)

        result = parser.parse(html, "raise")
        for key in comparative_data.keys():
            assert comparative_data[key] == result[key]
