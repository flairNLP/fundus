from collections import defaultdict
from textwrap import indent
from typing import Dict, Iterator, List, Optional, Set, Type, Union
from urllib.robotparser import RobotFileParser
from warnings import warn

import more_itertools
from requests.exceptions import ConnectionError, HTTPError, ReadTimeout
from typing_extensions import TypeAlias

from fundus.logging import create_logger
from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.session import session_handler
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, URLSource
from fundus.utils.iteration import iterate_all_subclasses

logger = create_logger(__name__)

FilterResult: TypeAlias = Union[List["FilteredPublisher"], List["Publisher"]]


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
            session = session_handler.get_session()
            response = session.get_with_interrupt(self.url, headers=headers)  # type: ignore[attr-defined]
        except HTTPError as err:
            if err.response.status_code in (401, 403):
                self.disallow_all = True
            elif 400 <= err.response.status_code < 500:
                self.allow_all = True
        else:
            self.parse(response.text.splitlines())


class Robots:
    def __init__(self, url: str):
        self.url = url
        self.robots_file_parser = CustomRobotFileParser(url)
        self.ready: bool = False

    def read(self, headers: Optional[Dict[str, str]] = None) -> None:
        try:
            self.robots_file_parser.read(headers=headers)
        except (ConnectionError, ReadTimeout):
            logger.warning(f"Could not load robots {self.url!r}. Ignoring robots and continuing.")
            self.robots_file_parser.allow_all = True
        self.ready = True

    def can_fetch(self, useragent: str, url: str) -> bool:
        return self.robots_file_parser.can_fetch(useragent, url)

    def crawl_delay(self, useragent: str) -> Optional[float]:
        delay = self.robots_file_parser.crawl_delay(useragent)
        return delay if delay is None else float(delay)


class Publisher:
    __name__: str
    __group__: "PublisherGroup"

    __SOURCE_ORDER__: Dict[Type[URLSource], int] = {
        RSSFeed: 1,
        NewsMap: 2,
        Sitemap: 3,
    }

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
        suppress_robots: bool = False,
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

        # Temporary fix to compensate for a bug in the RobotsFileParser treating rule lines
        # like /? as / disallowing the entire site. we could think about replacing the urllib
        # implementation with https://github.com/seomoz/reppy
        if suppress_robots:
            self.robots.robots_file_parser.allow_all = True

        source_mapping: Dict[Type[URLSource], List[URLSource]] = defaultdict(list)

        for url_source in sources:
            if not isinstance(url_source, URLSource):
                raise TypeError(
                    f"Unexpected type {type(url_source).__name__!r} as source for {self!r}. "
                    f"Allowed are {', '.join(repr(cls.__name__) for cls in iterate_all_subclasses(URLSource))}"
                )
            source_mapping[type(url_source)].append(url_source)

        self._source_mapping = dict(sorted(source_mapping.items(), key=lambda item: self.__SOURCE_ORDER__[item[0]]))

    @property
    def source_mapping(self) -> Dict[Type[URLSource], List[URLSource]]:
        return self._source_mapping

    @property
    def languages(self) -> Set[str]:
        return set.union(*(source.languages for sources in self.source_mapping.values() for source in sources))

    @property
    def source_types(self) -> Set[Type[URLSource]]:
        return set(self.source_mapping.keys())

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
        # we iterate source by source instead of checking self.languages and self.source_types,
        # because we need to know if there is a source supporting the given combination of
        # <source_types> and <languages>
        filtered_sources = [
            source
            for source in more_itertools.flatten(self.source_mapping.values())
            if (type(source) in source_types if source_types else True)
            and (source.languages & set(languages) if languages else True)
        ]

        return any(filtered_sources)


class FilteredPublisher(Publisher):
    """Publisher with prefiltered sources.

    Publisher with attached source types and languages to pre-filter sources.
    """

    def __init__(
        self, source_types: Optional[Set[Type[URLSource]]] = None, languages: Optional[Set[str]] = None, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.__source_types_filter__ = source_types or set()
        self.__language_filter__ = languages or set()

    @classmethod
    def from_publisher(
        cls,
        publisher: Publisher,
        source_types: Optional[Set[Type[URLSource]]] = None,
        languages: Optional[Set[str]] = None,
    ) -> "FilteredPublisher":
        new = FilteredPublisher.__new__(cls)

        # we create a deepcopy since the aware publisher is not included in the PublisherGroup
        new.__dict__.update(publisher.__dict__)
        new.__source_types_filter__ = source_types or set()
        new.__language_filter__ = languages or set()
        return new

    @property
    def source_mapping(self) -> Dict[Type[URLSource], List[URLSource]]:
        filtered_mapping: Dict[Type[URLSource], List[URLSource]] = {}

        # iterate over internal mapping to preserve order
        for source_type, sources in self._source_mapping.items():
            if self.__source_types_filter__ and source_type not in self.__source_types_filter__:
                continue

            filtered_sources = [
                source
                for source in sources
                if not self.__language_filter__ or source.languages & self.__language_filter__
            ]
            if filtered_sources:
                filtered_mapping[source_type] = filtered_sources

        return filtered_mapping

    @property
    def language_filter(self) -> Set[str]:
        return self.__language_filter__


class PublisherGroup(type):
    def __new__(cls, name, bases, attributes):
        new = super().__new__(cls, name, bases, attributes)

        # set __name__ and __group__
        for attribute, value in attributes.items():
            if isinstance(value, Publisher):
                value.__name__ = attribute
                value.__group__ = new
                if default_language := attributes.get("default_language"):
                    for source in more_itertools.flatten(value.source_mapping.values()):
                        if not source.languages:
                            source.languages = {default_language}

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
    ) -> Union[List[FilteredPublisher], List[Publisher]]:
        if not (attributes or source_types or languages):
            raise ValueError("You have to define at least one search condition")
        if not attributes:
            attributes = []
        if not languages:
            languages = []
        if not source_types:
            source_types = []

        matched: Union[List[FilteredPublisher], List[Publisher]] = []
        unique_attributes = set(attributes)
        spec: Publisher
        for publisher in cls:
            if unique_attributes.issubset(publisher.parser().attributes().names) and (
                publisher.supports(source_types=source_types, languages=languages)
            ):
                matched.append(
                    FilteredPublisher.from_publisher(
                        publisher,
                        source_types=set(source_types) & publisher.source_types,
                        languages=set(languages) & publisher.languages,
                    )
                )
        if not matched:
            warn("No publisher found matching the search criteria. Returning no publishers.")
        return matched
