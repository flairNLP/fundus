import ast
import datetime
import inspect
import pickle
import textwrap
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union

import lxml.html
import pytest

from fundus.parser import ArticleBody, LiveTickerBody
from fundus.parser.base_parser import (
    Attribute,
    AttributeCollection,
    BaseParser,
    ParserProxy,
    RegisteredFunction,
    attribute,
)
from fundus.parser.utility import generic_author_parsing
from fundus.publishers import PublisherCollection
from fundus.publishers.base_objects import Publisher
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.publication import LiveTicker
from fundus.scraping.scraper import BaseScraper
from tests.resources import attribute_annotations_mapping
from tests.utility import (
    get_meta_info_file,
    get_test_case_json,
    load_html_test_file_mapping,
    load_supported_publishers_markdown,
    load_test_case_data,
)


def test_supported_publishers_table():
    root = lxml.html.fromstring(load_supported_publishers_markdown())
    parsed_names: List[str] = root.xpath("//table[contains(@class,'publishers')]//td[1]/code/text()")
    for publisher in PublisherCollection:
        assert publisher.__name__ in parsed_names, (
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


# enforce test coverage for test parsing
# because this is also used for the generate_parser_test_files script we export it here
attributes_required_to_cover = {"title", "authors", "topics", "publishing_date", "body", "images"}

attributes_parsers_are_required_to_cover = {"body"}

# live tickers don't necessarily provide every attribute, e.g. authors or topics, so fewer are required
live_ticker_attributes_required_to_cover = {"title", "publishing_date", "body"}


# `BaseParser.body_selectors` locates a version's body selectors by convention: a selector passed as
# `<x>_selector` must live on the class as `_<x>_selector`. Nothing declares that, so where the name
# drifts, external tooling (skills/review-publisher) silently reads `None` instead of the selector.
# Enforced here until the selectors become declared class variables, see #958 - which retires this.
_BODY_SELECTOR_PARAMETERS = ("paragraph_selector", "summary_selector", "subheadline_selector")


def _called_name(func: ast.expr) -> Optional[str]:
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


def _misnamed_body_selectors(parser_class: Type[BaseParser]) -> List[str]:
    """Body selectors `parser_class` passes under a name `BaseParser.body_selectors` cannot find."""
    misnamed: List[str] = []
    for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(parser_class)))):
        if not isinstance(node, ast.Call) or _called_name(node.func) != "extract_article_body_with_selector":
            continue
        # extract_article_body_with_selector(doc, paragraph_selector, summary_selector, subheadline_selector, ...)
        arguments: List[Tuple[str, ast.expr]] = [
            (_BODY_SELECTOR_PARAMETERS[index - 1], argument)
            for index, argument in enumerate(node.args)
            if 1 <= index <= len(_BODY_SELECTOR_PARAMETERS)
        ]
        arguments += [
            (keyword.arg, keyword.value)
            for keyword in node.keywords
            if keyword.arg is not None and keyword.arg in _BODY_SELECTOR_PARAMETERS
        ]
        for parameter, value in arguments:
            # Only a `self.<attribute>` argument can be misnamed. An inline selector is invisible to
            # `body_selectors()` either way, which then reports "not declared" rather than "empty".
            if not (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name)):
                continue
            if value.value.id == "self" and value.attr != f"_{parameter}":
                misnamed.append(
                    f"{parser_class.__qualname__} passes {parameter}=self.{value.attr}, expected self._{parameter}"
                )
    return misnamed


@pytest.mark.parametrize(
    "publisher", list(PublisherCollection), ids=[publisher.__name__ for publisher in PublisherCollection]
)
class TestParser:
    def test_annotations(self, publisher: Publisher) -> None:
        parser_proxy = publisher.parser
        for versioned_parser in parser_proxy:
            assert attributes_parsers_are_required_to_cover.issubset(
                set(versioned_parser.attributes().validated.names)
            ), f"{versioned_parser.__name__!r} should implement at least {attributes_parsers_are_required_to_cover!r}"
            for attr in versioned_parser.attributes().validated:
                if annotation := attribute_annotations_mapping[attr.__name__]:
                    allowed = [annotation]
                    if attr.__name__ == "body":
                        # live ticker publishers may return a LiveTickerBody in addition to an ArticleBody
                        allowed.append(Optional[Union[ArticleBody, LiveTickerBody]])
                    assert attr.__annotations__.get("return") in allowed, (
                        f"Attribute {attr.__name__!r} for {versioned_parser.__name__!r} is of wrong type. "
                        f"{attr.__annotations__.get('return')} != {annotation}"
                    )
                else:
                    raise KeyError(f"Unsupported attribute {attr.__name__!r}")

    def test_body_selector_naming(self, publisher: Publisher) -> None:
        misnamed: List[str] = []
        for versioned_parser in publisher.parser:
            # Walk the MRO: `body` is often defined on V1 and inherited by the later versions.
            for parser_class in versioned_parser.__mro__:
                if not issubclass(parser_class, BaseParser) or parser_class is BaseParser:
                    continue
                misnamed += [entry for entry in _misnamed_body_selectors(parser_class) if entry not in misnamed]
        assert not misnamed, (
            f"{'; '.join(misnamed)}\n`BaseParser.body_selectors` finds a version's body selectors by name only, "
            f"so {publisher.name} silently reads as not declaring them (see #958)."
        )

    def test_parsing(self, publisher: Publisher) -> None:
        comparative_data = load_test_case_data(publisher)
        html_mapping = load_html_test_file_mapping(publisher)

        for versioned_parser in publisher.parser:
            # validate json
            version_name = versioned_parser.__name__
            assert (version_data := comparative_data.get(version_name)), (
                f"Missing test data for parser version {version_name!r}"
            )

            # validate test HTML
            assert (html := html_mapping.get(versioned_parser)), (
                f"Missing test HTML for parser version {version_name} of publisher {publisher.name}"
            )

            # re-instantiate parser to address deprecated attributes
            timestamp_instantiated_parser = publisher.parser(html.crawl_date)

            for key, value in version_data.items():
                if not value:
                    raise ValueError(
                        f"There is no value set for key {key!r} in the test JSON. "
                        f"Only complete articles should be used as test cases"
                    )

            # test coverage
            supported_attrs = set(timestamp_instantiated_parser.registered_attributes.names)
            missing_attrs = attributes_required_to_cover & supported_attrs - set(version_data.keys())
            assert not missing_attrs, (
                f"Test JSON for {version_name} of publisher {publisher.name} does not cover the following attribute(s): {missing_attrs}"
            )

            assert list(version_data.keys()) == sorted(attributes_required_to_cover & supported_attrs), (
                f"Test JSON for {version_name} is not in alphabetical order"
            )

            # compare data
            extraction = timestamp_instantiated_parser.parse(html.content, "raise")
            for key, value in version_data.items():
                assert value == extraction[key], f"{key!r} is not equal"

            # check if extraction is pickable
            pickle.dumps(extraction)

    def test_reserved_attribute_names(self, publisher: Publisher):
        parser = publisher.parser
        for attr in attribute_annotations_mapping.keys():
            if value := getattr(parser, attr, None):
                assert isinstance(value, Attribute), f"The name {attr!r} is reserved for attributes only."


class FixedSource:
    """An HTMLSource yielding the given HTML only."""

    def __init__(self, *htmls: HTML):
        self.htmls = htmls

    def fetch(self, url_filter=None) -> Iterator[HTML]:
        yield from self.htmls


def _supports_live_ticker(publisher: Publisher) -> bool:
    return any(versioned_parser.supports_live_tickers() for versioned_parser in publisher.parser)


live_ticker_publishers = [publisher for publisher in PublisherCollection if _supports_live_ticker(publisher)]


@pytest.mark.parametrize(
    "publisher", live_ticker_publishers, ids=[publisher.__name__ for publisher in live_ticker_publishers]
)
class TestLiveTickerParser:
    """Counterpart of `TestParser.test_parsing` for live tickers.

    Live tickers can't be found by crawling, so their test files are kept apart from the article test files
    (in a `live_ticker` subdirectory) and generated from explicit URLs:
    `python -m scripts.generate_parser_test_files -l -p <publisher> -u <live ticker url>`.
    """

    def test_parsing(self, publisher: Publisher) -> None:
        html_mapping = load_html_test_file_mapping(publisher, live_ticker=True)
        if not html_mapping and not get_test_case_json(publisher, live_ticker=True).path.exists():
            # live tickers can't be found by crawling, so not every publisher has a test case yet
            pytest.skip(f"No live ticker test case for {publisher.name} yet")
        comparative_data = load_test_case_data(publisher, live_ticker=True)

        # only versions implementing live ticker extraction need a live ticker test case
        for versioned_parser in publisher.parser:
            if not versioned_parser.supports_live_tickers():
                continue

            version_name = versioned_parser.__name__
            assert (version_data := comparative_data.get(version_name)), (
                f"Missing live ticker test data for parser version {version_name!r}"
            )
            assert (html := html_mapping.get(versioned_parser)), (
                f"Missing live ticker test HTML for parser version {version_name} of publisher {publisher.name}"
            )

            timestamp_instantiated_parser = publisher.parser(html.crawl_date)

            for key, value in version_data.items():
                if key == "topics":
                    # LiveTickers inherit topic parsing from the Article class, and it is not guaranteed to be supported
                    # for LiveTickers. If it is, it is enough to check for the Article test case.
                    continue
                if not value:
                    raise ValueError(
                        f"There is no value set for key {key!r} in the test JSON. "
                        f"Only complete live tickers should be used as test cases"
                    )

            supported_attrs = set(timestamp_instantiated_parser.registered_attributes.names)
            missing_attrs = live_ticker_attributes_required_to_cover & supported_attrs - set(version_data.keys())
            assert not missing_attrs, (
                f"Live ticker test JSON for {version_name} of publisher {publisher.name} "
                f"does not cover the following attribute(s): {missing_attrs}"
            )

            assert list(version_data.keys()) == sorted(version_data.keys()), (
                f"Live ticker test JSON for {version_name} is not in alphabetical order"
            )
            assert set(version_data.keys()) <= supported_attrs, (
                f"Live ticker test JSON for {version_name} contains unsupported attribute(s): "
                f"{set(version_data.keys()) - supported_attrs}"
            )

            extraction = timestamp_instantiated_parser.parse(html.content, "raise")

            body = extraction["body"]
            assert isinstance(body, LiveTickerBody), f"The test HTML for {version_name} is not a live ticker"
            assert body.entries, f"The live ticker of {version_name} has no entries"

            for key, value in version_data.items():
                assert value == extraction[key], f"{key!r} is not equal"

            pickle.dumps(extraction)

    def test_live_ticker_is_scraped_as_live_ticker(self, publisher: Publisher) -> None:
        for versioned_parser, html_file in load_html_test_file_mapping(publisher, live_ticker=True).items():
            html = HTML(
                content=html_file.content,
                crawl_date=html_file.crawl_date,
                requested_url=html_file.url,
                responded_url=html_file.url,
                source_info=SourceInfo(publisher.name),
            )
            scraper = BaseScraper(FixedSource(html), publisher_mapping={publisher.name: publisher})
            (publication,) = scraper.scrape(error_handling="raise")
            assert isinstance(publication, LiveTicker)
            assert list(publication), "iterating the live ticker should yield its entries as articles"


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
        for cc in PublisherCollection.get_subgroup_mapping().values():
            meta_file = get_meta_info_file(cc)
            meta_info = meta_file.load()
            assert meta_info, f"Meta info file {meta_file.path} is missing"
            assert sorted(meta_info.keys()) == list(meta_info.keys()), (
                f"Meta info file {meta_file.path} isn't ordered properly."
            )
