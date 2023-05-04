import datetime

import pytest

from fundus.parser.base_parser import Attribute, BaseParser, ParserProxy, attribute
from fundus.publishers import PublisherCollection
from fundus.publishers.base_objects import PublisherEnum
from tests.resources import attribute_annotations_mapping
from tests.utility import load_html_test_file_mapping, load_test_case_data


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
        assert len(BaseParser.attributes()) == 0
        assert len(parser_with_static_method.attributes()) == 0
        assert len(parser_with_attr_title.attributes()) == 1
        assert parser_with_attr_title.attributes().names == ["title"]

    def test_supported_unsupported(self):
        class ParserWithValidatedAndUnvalidated(BaseParser):
            VALID_UNTIL = datetime.date.today()

            @attribute
            def validated(self) -> str:
                return "supported"

            @attribute(validate=False)
            def unvalidated(self) -> str:
                return "unsupported"

        parser = ParserWithValidatedAndUnvalidated()
        assert len(parser.attributes()) == 2
        assert parser.attributes().validated == [parser.validated]
        assert parser.attributes().unvalidated == [parser.unvalidated]


class TestParserProxy:
    def test_empty_proxy(self, empty_parser_proxy):
        proxy = empty_parser_proxy()

        assert len(proxy) == 0
        assert len(proxy.attribute_mapping) == 0
        assert len(proxy.function_mapping) == 0

        with pytest.raises(AssertionError):
            proxy()

        with pytest.raises(AssertionError):
            proxy(datetime.date.today())

    def test_proxy_with_same_date(self):
        class ProxyWithSameDate(ParserProxy):
            class V2(BaseParser):
                VALID_UNTIL = datetime.date(2023, 1, 1)

            class V1(BaseParser):
                VALID_UNTIL = datetime.date(2023, 1, 1)

        with pytest.raises(AssertionError):
            ProxyWithSameDate()

    def test_proxy_with_two_versions(self):
        class ProxyWithTwoVersion(ParserProxy):
            class Later(BaseParser):
                VALID_UNTIL = datetime.datetime(2023, 1, 2).date()

            class Earlier(BaseParser):
                VALID_UNTIL = datetime.datetime(2023, 1, 1).date()

        proxy = ProxyWithTwoVersion()

        assert len(proxy) == 2

        for version in proxy:
            from_proxy = proxy(version.VALID_UNTIL)
            assert isinstance(from_proxy, version)
            assert from_proxy == proxy(version.VALID_UNTIL)


@pytest.mark.parametrize(
    "publisher", list(PublisherCollection), ids=[publisher.name for publisher in PublisherCollection]
)
class TestParser:
    def test_annotations(self, publisher: PublisherEnum) -> None:
        parser = publisher.parser
        for parser_version in parser:
            for attr in parser_version.attributes().validated:
                if annotation := attribute_annotations_mapping[attr.__name__]:
                    assert (
                            attr.__annotations__.get("return") == annotation
                    ), f"Attribute {attr.__name__} for {parser_version.__name__} failed"
                else:
                    raise KeyError(f"Unsupported attribute '{attr.__name__}'")

    def test_parsing(self, publisher: PublisherEnum) -> None:
        # enforce test coverage
        attrs_required_to_cover = {"title", "authors", "topics"}

        comparative_data = load_test_case_data(publisher)
        html_mapping = load_html_test_file_mapping(publisher)

        for version in publisher.parser:
            # validate json
            version_name = version.__name__
            assert (
                version_data := comparative_data.get(version_name)
            ), f"Missing test data for parser version '{version_name}'"
            assert version_data.get("meta"), f"Missing metadata for parser version '{version_name}'"
            assert (content := version_data.get("content")), f"Missing content for parser version '{version_name}'"

            # test coverage
            supported_attrs = set(version.attributes().names)
            missing_attrs = attrs_required_to_cover & supported_attrs - set(content.keys())
            assert not missing_attrs, f"Test JSON does not cover the following attribute(s): {missing_attrs}"

            assert (html := html_mapping.get(version)), f"Missing test HTML for parser version {version_name}"
            # compare data
            extraction = version().parse(html.content, "raise")
            for key, value in content.items():
                assert value == extraction[key]

    def test_reserved_attribute_names(self, publisher: PublisherEnum):
        parser = publisher.parser
        for attr in attribute_annotations_mapping.keys():
            if value := getattr(parser, attr, None):
                assert isinstance(value, Attribute), f"The name '{attr}' is reserved for attributes only."
