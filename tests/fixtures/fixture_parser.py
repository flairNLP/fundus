import pytest

from src.parser.html_parser import BaseParser, register_attribute


@pytest.fixture
def empty_parser():
    class EmptyParser(BaseParser):
        pass

    return EmptyParser


@pytest.fixture
def parser_with_attr_title():
    class ParserWithTitle(BaseParser):
        @register_attribute
        def title(self) -> str:
            return "This is a title"

    return ParserWithTitle
