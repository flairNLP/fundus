import datetime
from typing import List

import pytest

from fundus.parser import BaseParser, ParserProxy
from fundus.parser.base import RegisteredFunction


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

    def test_instances_of_same_proxy_compare_equal(self, proxy_with_two_versions_and_different_attrs):
        proxy = proxy_with_two_versions_and_different_attrs
        assert proxy() == proxy()
        assert hash(proxy()) == hash(proxy())

    def test_instances_of_different_proxies_compare_unequal(
        self, proxy_with_two_versions_and_different_attrs, proxy_with_two_deprecated_attributes
    ):
        assert proxy_with_two_versions_and_different_attrs() != proxy_with_two_deprecated_attributes()

    def test_not_equal_to_non_proxy(self, proxy_with_two_versions_and_different_attrs):
        assert proxy_with_two_versions_and_different_attrs() != "not a proxy"
