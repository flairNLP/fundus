import pytest

from src.parser.html_parser import BaseParser, attribute, function


@pytest.fixture
def empty_parser():
    class EmptyParser(BaseParser):
        pass

    return EmptyParser


@pytest.fixture
def parser_with_static_method():
    class ParserWithStaticMethod(BaseParser):
        @staticmethod
        def test():
            return "this is not an attribute"

    return ParserWithStaticMethod


@pytest.fixture
def parser_with_function_test():
    class ParserWithFunctionTest(BaseParser):
        @function
        def test(self):
            pass

    return ParserWithFunctionTest


@pytest.fixture
def parser_with_attr_title():
    class ParserWithAttrTitle(BaseParser):
        @attribute
        def title(self) -> str:
            return "This is a title"

    return ParserWithAttrTitle


@pytest.fixture
def parser_with_validated_and_unvalidated():
    class ParserWithValidatedAndUnvalidated(BaseParser):
        @attribute
        def validated(self) -> str:
            return "supported"

        @attribute(validate=False)
        def unvalidated(self) -> str:
            return "unsupported"

    return ParserWithValidatedAndUnvalidated
