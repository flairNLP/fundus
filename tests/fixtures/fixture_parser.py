from datetime import datetime

import pytest

from fundus.parser import BaseParser, ParserProxy, attribute, function


@pytest.fixture
def empty_parser_proxy():
    class EmptyParserProxy(ParserProxy):
        pass

    return EmptyParserProxy


@pytest.fixture()
def parser_proxy_with_version():
    class ParserProxyWithVersion(ParserProxy):
        class Version(BaseParser):
            VALID_UNTIL = datetime.now().date()

    return ParserProxyWithVersion


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
def proxy_with_two_versions_and_different_attrs():
    class ProxyWithTwoVersionsAndDifferentAttrs(ParserProxy):
        class Later(BaseParser):
            VALID_UNTIL = datetime(2023, 1, 2).date()

            @attribute
            def title(self) -> str:
                return "This is a title"

        class Earlier(BaseParser):
            VALID_UNTIL = datetime(2023, 1, 1).date()

            @attribute
            def another_title(self) -> str:
                return "This is a another title"

    return ProxyWithTwoVersionsAndDifferentAttrs
