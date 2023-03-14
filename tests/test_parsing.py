import json

from pathlib import Path
from typing import Dict


import pytest

from src.library.collection import PublisherCollection
from src.parser.html_parser import BaseParser

de_de = PublisherCollection.de_de


@pytest.mark.parametrize(
    "parser", [el.parser() for el in de_de], ids=[crawler.name for crawler in de_de]
)
class TestCrawling:
    def load_html(self, parser: BaseParser) -> str:
        name = parser.__class__.__name__
        file_source_path = Path(f"./tests/ressources/{name}.html").resolve()

        with open(
            file_source_path,
        ) as file:
            content = file.read()
        return content

    def load_data(self, parser: BaseParser) -> Dict:
        name = parser.__class__.__name__
        file_source_path = Path(f"./tests/ressources/{name}.json").resolve()

        with open(file_source_path) as file:
            content = file.read()

        return json.loads(content)

    def test_parsing(self, parser: BaseParser) -> None:
        input = self.load_html(parser)
        comparative_data = self.load_data(parser)

        result = parser.parse(input, "raise")
        for key_el in comparative_data.keys():
            assert comparative_data[key_el] == result[key_el]
