from datetime import datetime

import pytest

from fundus.parser import BaseParser, ParserProxy, attribute, function


@pytest.fixture
def empty_proxy():
    class EmptyProxy(ParserProxy):
        pass

    return EmptyProxy


@pytest.fixture
def proxy_with_two_versions():
    class ProxyWithTwoVersion(ParserProxy):
        class Later(BaseParser):
            VALID_UNTIL = datetime(2023, 1, 2).date()

        class Earlier(BaseParser):
            VALID_UNTIL = datetime(2023, 1, 1).date()

    return ProxyWithTwoVersion


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


@pytest.fixture
def parser_with_validated_and_unvalidated():
    class ParserWithValidatedAndUnvalidated(BaseParser):
        VALID_UNTIL = datetime.now().date()

        @attribute
        def validated(self) -> str:
            return "supported"

        @attribute(validate=False)
        def unvalidated(self) -> str:
            return "unsupported"

    return ParserWithValidatedAndUnvalidated
