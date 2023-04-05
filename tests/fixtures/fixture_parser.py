import pytest

from src.parsing import BaseParser, attribute


@pytest.fixture
def empty_parser():
    class EmptyParser(BaseParser):
        pass

    return EmptyParser


@pytest.fixture
def parser_with_attr_title():
    class ParserWithAttrTitle(BaseParser):
        @attribute
        def title(self) -> str:
            return "This is a title"

    return ParserWithAttrTitle
