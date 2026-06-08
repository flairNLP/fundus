import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest

from fundus.parser.base_parser import (
    AttributeCollection,
    BaseParser,
    ParserProxy,
    RegisteredFunction,
    attribute,
)
from fundus.parser.utility import generic_author_parsing


class TestBaseParser:
    def test_empty_parser(self):
        class ParserWithoutTime(BaseParser):
            pass

        ParserWithoutTime()

    def test_functions_iter(self, parser_with_function_test, parser_with_static_method):
        assert len(BaseParser.functions()) == 0
        assert len(parser_with_static_method.functions()) == 0
        assert len(parser_with_function_test.functions()) == 1
        assert parser_with_function_test.functions().names == ["test"]

    def test_attributes_iter(self, parser_with_attr_title, parser_with_static_method):
        assert len(BaseParser.attributes()) == 1
        assert len(parser_with_static_method.attributes()) == 1
        assert len(parser_with_attr_title.attributes()) == 2
        assert parser_with_attr_title.attributes().names == ["free_access", "title"]

    def test_supported_unsupported(self):
        class ParserWithValidatedAndUnvalidated(BaseParser):
            @attribute
            def validated(self) -> str:
                return "supported"

            @attribute(validate=False)
            def unvalidated(self) -> str:
                return "unsupported"

        parser = ParserWithValidatedAndUnvalidated()
        assert len(parser.attributes()) == 3

        assert (validated := parser.attributes().validated)
        assert isinstance(validated, AttributeCollection)
        assert (funcs := list(validated)) != [parser.validated]
        assert funcs[1].__func__ == parser.validated.__func__

        assert (unvalidated := parser.attributes().unvalidated)
        assert isinstance(validated, AttributeCollection)
        assert (funcs := list(unvalidated)) != [parser.unvalidated]
        assert funcs[0].__func__ == parser.unvalidated.__func__

    def test_default_values_for_attributes(self):
        class Parser(BaseParser):
            @attribute
            def test_optional(self) -> Optional[str]:
                raise Exception

            @attribute
            def test_collection(self) -> Tuple[str, ...]:
                raise Exception

            @attribute
            def test_nested_collection(self) -> List[Tuple[str, str]]:
                raise Exception

            @attribute(default_factory=lambda: "This is a default")
            def test_default_factory(self) -> Union[str, bool]:
                raise Exception

            @attribute
            def test_boolean(self) -> bool:
                raise Exception

        parser = Parser()

        default_values = {attr.__name__: attr.__default__ for attr in parser.attributes()}

        expected_values: Dict[str, Any] = {
            "test_optional": None,
            "test_collection": tuple(),
            "test_nested_collection": list(),
            "test_default_factory": "This is a default",
            "test_boolean": False,
            "free_access": False,
        }

        for name, value in default_values.items():
            assert value == expected_values[name]

        class ParserWithUnion(BaseParser):
            @attribute
            def this_should_fail(self) -> Union[str, bool]:
                raise Exception

        parser_with_union = ParserWithUnion()

        with pytest.raises(NotImplementedError):
            default_values = {attr.__name__: attr.__default__ for attr in parser_with_union.attributes()}


class TestParserProxy:
    def test_empty_proxy(self, empty_parser_proxy):
        parser_proxy = empty_parser_proxy

        with pytest.raises(ValueError):
            parser_proxy()

    def test_proxy_with_same_date(self):
        class ProxyWithSameDate(ParserProxy):
            class V2(BaseParser):
                VALID_UNTIL = datetime.date(2023, 1, 1)

            class V1(BaseParser):
                VALID_UNTIL = datetime.date(2023, 1, 1)

        with pytest.raises(ValueError):
            ProxyWithSameDate()

    def test_len(self, proxy_with_two_versions_and_different_attrs):
        parser_proxy = proxy_with_two_versions_and_different_attrs()
        assert len(parser_proxy) == 2

    def test_iter(self, proxy_with_two_versions_and_different_attrs):
        versioned_parsers = list(proxy_with_two_versions_and_different_attrs())
        assert versioned_parsers[0].VALID_UNTIL > versioned_parsers[1].VALID_UNTIL

    def test_latest(self, proxy_with_two_versions_and_different_attrs):
        parser_proxy = proxy_with_two_versions_and_different_attrs()
        print(parser_proxy.latest_version.__name__)
        assert parser_proxy.latest_version == parser_proxy.Later

    def test_call(self, proxy_with_two_versions_and_different_attrs):
        parser_proxy = proxy_with_two_versions_and_different_attrs()
        assert type(parser_proxy()) is parser_proxy.latest_version

        for versioned_parser in parser_proxy:
            from_proxy = parser_proxy(versioned_parser.VALID_UNTIL)
            assert isinstance(from_proxy, versioned_parser)
            assert from_proxy == parser_proxy(versioned_parser.VALID_UNTIL)

    def test_mapping(self, proxy_with_two_versions_and_different_attrs):
        parser_proxy = proxy_with_two_versions_and_different_attrs()

        for versioned_parser in parser_proxy:
            assert versioned_parser.attributes() == parser_proxy.attribute_mapping[versioned_parser]

        attrs1, attrs2 = parser_proxy.attribute_mapping.values()
        assert attrs1.names != attrs2.names

    def test_deprecated(self, proxy_with_two_deprecated_attributes):
        def get_initialized_attrs(parser: BaseParser) -> List[RegisteredFunction]:
            return parser._sorted_registered_functions

        proxy: ParserProxy = proxy_with_two_deprecated_attributes()

        number_of_attributes = len(proxy.latest_version.attributes(include_all=True))

        parser1 = proxy(datetime.date(2023, 1, 1))
        assert len(parser1.registered) == number_of_attributes

        parser2 = proxy(datetime.date(2024, 3, 1))
        assert len(parser2.registered) == number_of_attributes - 1

        parser3 = proxy(datetime.date(2024, 4, 1))
        assert len(parser3.registered) == number_of_attributes - 2

        assert parser3 == proxy(datetime.date(2024, 5, 1))
        assert parser3 != parser2 != parser1


class TestUtility:
    def test_generic_author_parsing(self):
        # type None
        assert generic_author_parsing(None) == []

        # type str
        assert generic_author_parsing("Peter") == ["Peter"]
        assert generic_author_parsing("Peter , Funny") == ["Peter", "Funny"]
        test_string = "Peter und Funny and the seven dandelions, right;?,;"
        assert generic_author_parsing(test_string) == ["Peter", "Funny", "the seven dandelions", "right", "?"]
        assert generic_author_parsing(test_string, split_on=["Funny", "dandelions"]) == [
            "Peter und",
            "and the seven",
            ", right;?,;",
        ]

        # type dict
        assert generic_author_parsing({"name": "Peter Funny"}) == ["Peter Funny"]
        assert generic_author_parsing({}) == generic_author_parsing({"what": "ever"}) == []

        # type list[str]
        assert generic_author_parsing([" Now", "we", "test ", " strip ", " ping ? "]) == [
            "Now",
            "we",
            "test",
            "strip",
            "ping ?",
        ]

        # type list[dict]
        assert generic_author_parsing(
            [{"name": "Peter Funny"}, {"name": "Funny Peter"}, {"this": "is not a pipe"}, {}]  # type: ignore
        ) == ["Peter Funny", "Funny Peter"]
        assert generic_author_parsing([{}]) == generic_author_parsing([{}, {"wrong": "key"}]) == []  # type: ignore
