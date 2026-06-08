import pickle
from typing import List

import lxml.html

from fundus import PublisherCollection
from fundus.parser.base_parser import Attribute
from fundus.publishers import Publisher
from tests.resources import attribute_annotations_mapping
from tests.utility import (
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


# enforce test coverage for test parsing
# because this is also used for the generate_parser_test_files script we export it here
attributes_required_to_cover = {"title", "authors", "topics", "publishing_date", "body", "images"}

attributes_parsers_are_required_to_cover = {"body"}


class TestPublisherParsers:
    def test_annotations(self, publisher: Publisher) -> None:
        parser_proxy = publisher.parser
        for versioned_parser in parser_proxy:
            assert attributes_parsers_are_required_to_cover.issubset(
                set(versioned_parser.attributes().validated.names)
            ), f"{versioned_parser.__name__!r} should implement at least {attributes_parsers_are_required_to_cover!r}"
            for attr in versioned_parser.attributes().validated:
                annotation = attribute_annotations_mapping.get(attr.__name__)
                assert annotation, (
                    f"Attribute {attr.__name__!r} has no registered annotation in attribute_annotations_mapping"
                )
                assert attr.__annotations__.get("return") == annotation, (
                    f"Attribute {attr.__name__!r} for {versioned_parser.__name__!r} is of wrong type. "
                    f"{attr.__annotations__.get('return')} != {annotation}"
                )

    def test_test_data_wellformed(self, publisher: Publisher) -> None:
        """Validate the test fixture: it exists, is complete, and matches the parser's required attributes."""
        comparative_data = load_test_case_data(publisher)
        html_mapping = load_html_test_file_mapping(publisher)

        for versioned_parser in publisher.parser:
            version_name = versioned_parser.__name__

            assert (version_data := comparative_data.get(version_name)), (
                f"Missing test data for parser version {version_name!r}"
            )
            assert (html := html_mapping.get(versioned_parser)), (
                f"Missing test HTML for parser version {version_name} of publisher {publisher.name}"
            )

            # only complete articles should be used as test cases
            for key, value in version_data.items():
                assert value, (
                    f"There is no value set for key {key!r} in the test JSON. "
                    f"Only complete articles should be used as test cases"
                )

            # the fixture must cover the parser's required attributes, in alphabetical order;
            # re-instantiate parser to address deprecated attributes
            timestamp_instantiated_parser = publisher.parser(html.crawl_date)
            supported_attrs = set(timestamp_instantiated_parser.registered_attributes.names)
            missing_attrs = attributes_required_to_cover & supported_attrs - set(version_data.keys())
            assert not missing_attrs, (
                f"Test JSON for {version_name} of publisher {publisher.name} does not cover the following attribute(s): {missing_attrs}"
            )
            assert list(version_data.keys()) == sorted(attributes_required_to_cover & supported_attrs), (
                f"Test JSON for {version_name} is not in alphabetical order"
            )

    def test_extraction_matches(self, publisher: Publisher) -> None:
        """Validate the parser: its extraction matches the expected fixture data and is picklable."""
        comparative_data = load_test_case_data(publisher)
        html_mapping = load_html_test_file_mapping(publisher)

        for versioned_parser in publisher.parser:
            version_name = versioned_parser.__name__

            assert (version_data := comparative_data.get(version_name)), (
                f"Missing test data for parser version {version_name!r}"
            )
            assert (html := html_mapping.get(versioned_parser)), (
                f"Missing test HTML for parser version {version_name} of publisher {publisher.name}"
            )

            # re-instantiate parser to address deprecated attributes
            timestamp_instantiated_parser = publisher.parser(html.crawl_date)

            extraction = timestamp_instantiated_parser.parse(html.content)
            for key, value in version_data.items():
                assert value == extraction[key], f"{key!r} is not equal"

            # check if extraction is pickable
            pickle.dumps(extraction)

    def test_reserved_attribute_names(self, publisher: Publisher):
        parser = publisher.parser
        for attr in attribute_annotations_mapping.keys():
            if value := getattr(parser, attr, None):
                assert isinstance(value, Attribute), f"The name {attr!r} is reserved for attributes only."
