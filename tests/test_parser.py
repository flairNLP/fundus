import datetime
from typing import List

import lxml.html
import pytest

from fundus.parser.base_parser import (
    Attribute,
    AttributeCollection,
    BaseParser,
    ParserProxy,
    attribute,
)
from fundus.parser.utility import generic_author_parsing
from fundus.publishers import PublisherCollection
from fundus.publishers.base_objects import PublisherEnum
from tests.resources import attribute_annotations_mapping
from tests.utility import (
    get_meta_info_file,
    load_html_test_file_mapping,
    load_supported_publishers_markdown,
    load_test_case_data,
)


def test_supported_publishers_table():
    root = lxml.html.fromstring(load_supported_publishers_markdown())
    parsed_names: List[str] = root.xpath("//table[contains(@class,'publishers')]//code/text()")
    for publisher in PublisherCollection:
        assert publisher.name in parsed_names, (
            f"Publisher {publisher.name} is not included in docs/supported_news.md. "
            f"Run 'python -m scripts.generate_tables'"
        )


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
            @attribute
            def validated(self) -> str:
                return "supported"

            @attribute(validate=False)
            def unvalidated(self) -> str:
                return "unsupported"

        parser = ParserWithValidatedAndUnvalidated()
        assert len(parser.attributes()) == 2

        assert (validated := parser.attributes().validated)
        assert isinstance(validated, AttributeCollection)
        assert (funcs := list(validated)) != [parser.validated]
        assert funcs[0].__func__ == parser.validated.__func__

        assert (unvalidated := parser.attributes().unvalidated)
        assert isinstance(validated, AttributeCollection)
        assert (funcs := list(unvalidated)) != [parser.unvalidated]
        assert funcs[0].__func__ == parser.unvalidated.__func__


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
        assert type(parser_proxy()) == parser_proxy.latest_version

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


# enforce test coverage for test parsing
# because this is also used for the generate_parser_test_files script we export it here
attributes_required_to_cover = {"title", "authors", "topics", "publishing_date"}


@pytest.mark.parametrize(
    "publisher", list(PublisherCollection), ids=[publisher.name for publisher in PublisherCollection]
)
class TestParser:
    def test_annotations(self, publisher: PublisherEnum) -> None:
        parser_proxy = publisher.parser
        for versioned_parser in parser_proxy:
            for attr in versioned_parser.attributes().validated:
                if annotation := attribute_annotations_mapping[attr.__name__]:
                    assert (
                        attr.__annotations__.get("return") == annotation
                    ), f"Attribute {attr.__name__} for {versioned_parser.__name__} failed"
                else:
                    raise KeyError(f"Unsupported attribute '{attr.__name__}'")

    def test_parsing(self, publisher: PublisherEnum) -> None:
        comparative_data = load_test_case_data(publisher)
        html_mapping = load_html_test_file_mapping(publisher)

        for versioned_parser in publisher.parser:
            # validate json
            version_name = versioned_parser.__name__
            assert (
                version_data := comparative_data.get(version_name)
            ), f"Missing test data for parser version '{version_name}'"

            for key, value in version_data.items():
                if not value:
                    raise ValueError(
                        f"There is no value set for key '{key}' in the test JSON. "
                        f"Only complete articles should be used as test cases"
                    )

            # test coverage
            supported_attrs = set(versioned_parser.attributes().names)
            missing_attrs = attributes_required_to_cover & supported_attrs - set(version_data.keys())
            assert not missing_attrs, f"Test JSON does not cover the following attribute(s): {missing_attrs}"

            assert (html := html_mapping.get(versioned_parser)), f"Missing test HTML for parser version {version_name}"
            # compare data
            extraction = versioned_parser().parse(html.content, "raise")
            for key, value in version_data.items():
                assert value == extraction[key]

    def test_reserved_attribute_names(self, publisher: PublisherEnum):
        parser = publisher.parser
        for attr in attribute_annotations_mapping.keys():
            if value := getattr(parser, attr, None):
                assert isinstance(value, Attribute), f"The name '{attr}' is reserved for attributes only."


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


class TestMetaInfo:
    def test_order(self):
        for cc in PublisherCollection.get_publisher_enum_mapping().values():
            meta_file = get_meta_info_file(next(iter(cc)))
            meta_info = meta_file.load()
            assert meta_info, f"Meta info file {meta_file.path} is missing"
            assert sorted(meta_info.keys()) == list(meta_info.keys()), (
                f"Meta info file {meta_file.path} " f"isn't ordered properly."
            )
