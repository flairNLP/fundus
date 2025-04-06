import inspect
from textwrap import indent
from typing import Dict, Iterator, List, Optional, Set, Type, Union
from urllib.robotparser import RobotFileParser
from warnings import warn

import requests

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, URLSource
from fundus.utils.iteration import iterate_all_subclasses


class CustomRobotFileParser(RobotFileParser):
    """Monkey patch RobotFileParse

    This class overwrites the read() methode of RobotFileParser to use the <requests> pkg instead of urllib.
    This is in order to avoid 403 errors when fetching the robots.txt file.
    """

    # noinspection PyAttributeOutsideInit
    def read(self, headers: Optional[Dict[str, str]] = None) -> None:
        """Reads the robots.txt URL and feeds it to the parser."""
        try:
            # noinspection PyUnresolvedReferences
            f = requests.Session().get(self.url, headers=headers)  # type: ignore[attr-defined]
            f.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code in (401, 403):
                self.disallow_all = True
            elif 400 <= err.response.status_code < 500:
                self.allow_all = True
        else:
            self.parse(f.text.splitlines())


class Robots:
    def __init__(self, url: str):
        self.url = url
        self.robots_file_parser = CustomRobotFileParser(url)
        self.ready: bool = False

    def read(self, headers: Optional[Dict[str, str]] = None) -> None:
        self.robots_file_parser.read(headers=headers)
        self.ready = True

    def can_fetch(self, useragent: str, url: str) -> bool:
        return self.robots_file_parser.can_fetch(useragent, url)

    def crawl_delay(self, useragent: str) -> Optional[float]:
        delay = self.robots_file_parser.crawl_delay(useragent)
        return delay if delay is None else float(delay)


class Publisher:
    __name__: str
    __group__: "PublisherGroup"
    _language_filter: Set[str] = set()

    def __init__(
        self,
        name: str,
        domain: str,
        parser: Type[ParserProxy],
        sources: List[URLSource],
        query_parameter: Optional[Dict[str, str]] = None,
        url_filter: Optional[URLFilter] = None,
        request_header: Optional[Dict[str, str]] = None,
        deprecated: bool = False,
    ):
        """Initialization of a new Publisher object

        Args:
            name (str): Name of the publisher, as it would appear on the website
            domain (str): The domain of the publishers website
            parser (Type[ParserProxy]): Corresponding ParserProxy Object
            sources (List[URLSource]): List of sources for articles from the publishers
            query_parameter (Optional[Dict[str, str]]): Dictionary of query parameter: content to be
                appended to crawled URLs
            url_filter (Optional[URLFilter]): Regex filter to apply determining URLs to be skipped
            request_header (Optional[Dict[str, str]]): Request header to be used for the GET-request

        """
        if not (name and domain and parser and sources):
            raise ValueError("Failed to create Publisher. Name, Domain, Parser and Sources are mandatory")
        self.name = name
        self.parser = parser()
        self.domain = domain
        self.query_parameter = query_parameter
        self.url_filter = url_filter
        self.request_header = request_header
        self.deprecated = deprecated
        self.robots = Robots(self.domain + "robots.txt" if self.domain.endswith("/") else self.domain + "/robots.txt")
        # we define the dict here manually instead of using default dict so that we can control
        # the order in which sources are proceeded.
        source_mapping: Dict[Type[URLSource], List[URLSource]] = {
            RSSFeed: [],
            NewsMap: [],
            Sitemap: [],
        }

        for url_source in sources:
            if not isinstance(url_source, URLSource):
                raise TypeError(
                    f"Unexpected type {type(url_source).__name__!r} as source for {self!r}. "
                    f"Allowed are {', '.join(repr(cls.__name__) for cls in iterate_all_subclasses(URLSource))}"
                )
            source_mapping[type(url_source)].append(url_source)

        self._source_mapping = source_mapping

    @property
    def source_mapping(self) -> Dict[Type[URLSource], List[URLSource]]:
        if not self._language_filter:
            return self._source_mapping
        filtered_mapping = {}
        for source_type, sources in self._source_mapping.items():
            filtered_mapping[source_type] = [source for source in sources if source.languages & self._language_filter]
        return filtered_mapping

    def __str__(self) -> str:
        return f"{self.name}"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Publisher):
            return False
        return (
            self.name == other.name
            and self.parser == other.parser
            and self.domain == other.domain
            and self.source_mapping == other.source_mapping
            and self.query_parameter == other.query_parameter
            and self.url_filter == other.url_filter
            and self.request_header == other.request_header
        )

    def supports(
        self, source_types: Optional[List[Type[URLSource]]] = None, languages: Optional[List[str]] = None
    ) -> bool:
        if source_types is None:
            supports_sources = True
        elif not isinstance(source_types, list):
            raise ValueError(f"Expected list of source types, got {type(source_types).__name__!r}")
        else:
            for source_type in source_types:
                if not inspect.isclass(source_type) or not issubclass(source_type, URLSource):
                    raise TypeError(
                        f"Got unexpected type {source_type!r}. "
                        f"Allowed are {', '.join(repr(self.__name__) for self in iterate_all_subclasses(URLSource))}"
                    )
            supports_sources = all(bool(self.source_mapping.get(source_type)) for source_type in source_types)
        if languages is None:
            supports_languages = True
        elif not isinstance(languages, list):
            raise ValueError(f"Expected list of languages, got {type(languages).__name__!r}")
        else:
            supports_languages = False
            unique_languages = set(languages)
            for sources in self._source_mapping.values():
                for source in sources:
                    if source.languages & unique_languages:
                        self._language_filter = unique_languages
                        supports_languages = True
                        break
        return supports_sources and supports_languages


class PublisherGroup(type):
    def __new__(cls, name, bases, attributes):
        new = super().__new__(cls, name, bases, attributes)

        # set __name__ and __group__
        for attribute, value in attributes.items():
            if isinstance(value, Publisher):
                value.__name__ = attribute
                value.__group__ = new
                if attributes.get("default_language"):
                    for source_type in value.source_mapping.values():
                        for source in source_type:
                            if not source.languages:
                                source.languages = {attributes["default_language"]}

        return new

    @property
    def mapping(cls) -> Dict[str, Union[Publisher, "PublisherGroup"]]:
        return {name: value for name, value in cls.__dict__.items() if isinstance(value, (Publisher, PublisherGroup))}

    def get_subgroup_mapping(cls) -> Dict[str, "PublisherGroup"]:
        return {name: value for name, value in cls.__dict__.items() if isinstance(value, PublisherGroup)}

    def __iter__(cls) -> Iterator[Publisher]:
        """This will iterate over all publishers included in the group and its subgroups.

        Returns:
            Iterator[Publisher]: Iterator over publishers included in the group and its subgroups.

        """
        for attribute in cls.__dict__.values():
            if isinstance(attribute, Publisher):
                yield attribute
            elif isinstance(attribute, PublisherGroup):
                yield from attribute

    def __getitem__(cls, name: str) -> Publisher:
        """Get a publisher from the collection by name represented as string.

        Args:
            name: A string referencing the publisher in the corresponding enum.

        Returns:
            Publisher: The corresponding publisher.

        """
        return {publisher.__name__: publisher for publisher in cls}[name]

    def __len__(cls) -> int:
        """The number of publishers included in the group.

        Returns:
            int: The number of publishers.
        """
        return len(list(cls.__iter__()))

    def __str__(cls) -> str:
        representation = f"<{cls.__name__}: {len(cls)}>"
        for name, element in cls.mapping.items():
            representation += "\n" + indent(str(element), prefix="\t")
        return representation

    def search(
        cls,
        attributes: Optional[List[str]] = None,
        source_types: Optional[List[Type[URLSource]]] = None,
        languages: Optional[List[str]] = None,
    ) -> List[Publisher]:
        if not (attributes or source_types or languages):
            raise ValueError("You have to define at least one search condition")
        if not attributes:
            attributes = []
        if not languages:
            languages = []
        matched = []
        unique_attributes = set(attributes)
        spec: Publisher
        for publisher in cls:
            if (
                unique_attributes.issubset(publisher.parser().attributes().names)
                and (publisher.supports(source_types=source_types) if source_types else True)
                and (publisher.supports(languages=languages) if languages else True)
            ):
                matched.append(publisher)
        if not matched:
            warn("No publisher found matching the search criteria. Returning no publishers.")
        return matched
