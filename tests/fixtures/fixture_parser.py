from datetime import datetime

import pytest

from fundus.parser import BaseParser, ParserProxy, attribute, function


@pytest.fixture
def empty_parser_proxy():
    class EmptyParserProxy(ParserProxy):
        pass

    return EmptyParserProxy


@pytest.fixture
def parser_with_static_method():
    class ParserWithStaticMethod(BaseParser):
        VALID_UNTIL = datetime.now().date()

        @staticmethod
        def test():
            return "this is not an attribute"

    return ParserWithStaticMethod


@pytest.fixture
def parser_with_function_test():
    class ParserWithFunctionTest(BaseParser):
        VALID_UNTIL = datetime.now().date()

        @function
        def test(self):
            pass

    return ParserWithFunctionTest


@pytest.fixture
def parser_with_attr_title():
    class ParserWithAttrTitle(BaseParser):
        VALID_UNTIL = datetime.now().date()

        @attribute
        def title(self) -> str:
            return "This is a title"

    return ParserWithAttrTitle
