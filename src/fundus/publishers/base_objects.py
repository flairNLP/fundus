import copy
from collections import defaultdict
from textwrap import indent
from typing import Dict, FrozenSet, Iterable, Iterator, List, Optional, Set, Type, Union
from warnings import warn

from curl_cffi.requests import BrowserType, BrowserTypeLiteral
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, Timeout
from curl_cffi.requests.impersonate import normalize_browser_type
from robots import RobotFileParser

from fundus.logging import create_logger
from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.session import _default_header, session_handler
from fundus.scraping.url import SourceHandler, URLSource

logger = create_logger(__name__)


class CustomRobotFileParser(RobotFileParser):
    """Monkey patch RobotFileParse

    This class overwrites the read() methode of RobotFileParser to use the <requests> pkg instead of urllib.
    This is in order to avoid 403 errors when fetching the robots.txt file.
    """

    _disallow_training_keywords: Set[str] = {
        "machine",
        "learning",
        "training",
        "train",
        "model",
        "models",
        "artificial",
        "intelligence",
        "large",
        "language",
        "llm",
        "llms",
    }

    def __init__(
        self, url: str, headers: Optional[Dict[str, str]] = None, impersonate: Optional[BrowserTypeLiteral] = None
    ):
        self.headers = headers
        self.disallows_training: bool = False
        self.url = url
        self.impersonate = impersonate
        super().__init__(url)

    # noinspection PyAttributeOutsideInit
    def read(self) -> None:
        """Reads the robots.txt URL and feeds it to the parser."""
        try:
            # noinspection PyUnresolvedReferences
            session = session_handler.get_session(self.impersonate)
            response = session.get_with_interrupt(self.url, headers=self.headers)
        except HTTPError as err:
            if err.response.status_code in (401, 403):
                logger.warning(
                    f"Robots {self.url!r} disallowed access with status code {err.response.status_code}."
                    " Defaulting to disallow all."
                )
                self.disallow_all = True
            elif 400 <= err.response.status_code < 500:
                self.allow_all = True
        else:
            self.parse(response.text.splitlines())

    def parse(self, lines: Iterable[str]) -> None:
        for line in lines:
            if line.strip().startswith("#") and set(line.split(" ")) & self._disallow_training_keywords:
                self.disallows_training = True
                break
        super().parse(lines)


class Robots:
    def __init__(
        self, url: str, headers: Optional[Dict[str, str]] = None, impersonate: Optional[BrowserTypeLiteral] = None
    ):
        self.url = url
        self.robots_file_parser = CustomRobotFileParser(url, headers=headers, impersonate=impersonate)
        self.ready: bool = False

    def _read(self) -> None:
        try:
            self.robots_file_parser.read()
        except (ConnectionError, Timeout):
            logger.warning(f"Could not load robots {self.url!r}. Ignoring robots and continuing.")
            self.robots_file_parser.allow_all = True
        self.ready = True

    def ensure_ready(self) -> None:
        """Ensure that the robots.txt file is read and parsed."""
        if not self.ready:
            self._read()

    def can_fetch(self, useragent: str, url: str) -> bool:
        self.ensure_ready()
        return self.robots_file_parser.can_fetch(useragent, url)

    def crawl_delay(self, useragent: str) -> Optional[float]:
        self.ensure_ready()
        delay = self.robots_file_parser.crawl_delay(useragent)
        return delay if delay is None else float(delay)

    def disallows_training(self) -> bool:
        self.ensure_ready()
        return self.robots_file_parser.disallows_training

    def disallow_all(self) -> bool:
        self.ensure_ready()
        return self.robots_file_parser.disallow_all


def _narrow_languages(
    current: Optional[FrozenSet[str]], languages: Optional[Iterable[str]]
) -> Optional[FrozenSet[str]]:
    """Intersects <current> with <languages>, with None standing for no restriction at all.

    Intersecting rather than replacing keeps restrictions from widening each other, so that
    narrowing an already narrowed publisher can only ever remove languages.
    """
    if not languages:
        return current
    return frozenset(languages) if current is None else current & frozenset(languages)


class Publisher:
    __name__: str
    __group__: "PublisherGroup"

    def __init__(
        self,
        name: str,
        domain: str,
        parser: Type[ParserProxy],
        sources: List[URLSource],
        query_parameter: Optional[Dict[str, str]] = None,
        url_filter: Optional[URLFilter] = None,
        request_header: Dict[str, str] = _default_header,
        deprecated: bool = False,
        disallows_training: bool = False,
        suppress_robots: bool = False,
        impersonate: Optional[BrowserTypeLiteral] = None,
        deprecated_domains: Optional[List[str]] = None,
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
            deprecated (bool): If True, the publisher is deprecated and skipped by default
            disallows_training (bool): If True, the publisher disallows training on its articles in
                its robots.txt file. Note that this is only an indicator and users should verify the
                terms of use of the publisher before using the articles for training purposes.
            suppress_robots (bool): If True, robots.txt restrictions are ignored for this publisher
            impersonate (Optional[str]): Browser profile to impersonate via CurlCffiAdapter, e.g.
                "chrome" or "safari". If set, requests to this publisher use curl_cffi instead of
                the standard urllib3 stack, which can bypass TLS fingerprint-based bot detection.
                Check https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html for browser targets.
            deprecated_domains (Optional[List[str]]): List of domains that are deprecated. This is used to handle domain
                migration by publishers in order to support CCNewsCrawling

        """
        if not (name and domain and parser and sources):
            raise ValueError("Failed to create Publisher. Name, Domain, Parser and Sources are mandatory")

        if (
            impersonate is not None
            and (impersonate := normalize_browser_type(impersonate)) not in BrowserType._value2member_map_
        ):
            raise ValueError(
                f"Browser type <{impersonate}> not supported. Supported types are: "
                f"{', '.join(BrowserType._value2member_map_.keys())}"
            )

        self.name = name
        self.parser = parser()
        self.domain = domain
        self.query_parameter = query_parameter
        self.url_filter = url_filter
        self.request_header = request_header
        self.impersonate = impersonate
        self.deprecated = deprecated
        self.robots = Robots(
            url=self.domain + "robots.txt" if self.domain.endswith("/") else self.domain + "/robots.txt",
            headers=self.request_header,
            impersonate=impersonate,
        )
        self._disallows_training = disallows_training
        self.deprecated_domains = deprecated_domains or []

        # Temporary fix to compensate for a bug in the RobotsFileParser treating rule lines
        # like /? as / disallowing the entire site. we could think about replacing the urllib
        # implementation with https://github.com/seomoz/reppy
        if suppress_robots:
            self.robots.robots_file_parser.allow_all = True

        self._sources = SourceHandler(sources)
        self._language_filter: Optional[FrozenSet[str]] = None

    @property
    def disallows_training(self) -> bool:
        return self._disallows_training or self.robots.disallows_training()

    @property
    def sources(self) -> SourceHandler:
        return self._sources

    @property
    def source_mapping(self) -> Dict[Type[URLSource], List[URLSource]]:
        """Deprecated view on <sources>, grouped by source type and kept in crawl order."""
        mapping: Dict[Type[URLSource], List[URLSource]] = defaultdict(list)
        for source in self.sources:
            mapping[type(source)].append(source)
        return dict(mapping)

    @property
    def languages(self) -> Set[str]:
        return self.sources.languages

    @property
    def source_types(self) -> Set[Type[URLSource]]:
        return self.sources.source_types

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
            and self.sources == other.sources
            and self.query_parameter == other.query_parameter
            and self.url_filter == other.url_filter
            and self.request_header == other.request_header
        )

    def supports(
        self, source_types: Optional[List[Type[URLSource]]] = None, languages: Optional[List[str]] = None
    ) -> bool:
        """Whether this publisher has a source left to contribute under the given restrictions.

        Restrictions it already carries and the given ones have to be met by one and the same
        source, since a publisher covering a language through one source and a source type through
        another covers neither combination. Called without arguments, this asks whether anything
        survived the restrictions it carries.
        """
        # a publisher restricted to languages excluding each other supports nothing, even where a
        # source declaring both survived the filtering, since no article of it could be kept
        if _narrow_languages(self._language_filter, languages) == frozenset():
            return False

        # we filter instead of checking self.languages and self.source_types, because we need to
        # know if there is a single source supporting the given combination of <source_types>
        # and <languages>
        return bool(self.sources.filter(source_types=source_types, languages=languages))

    @property
    def language_filter(self) -> Optional[FrozenSet[str]]:
        """The languages this publisher was restricted to, or None if it was not restricted.

        Kept next to the narrowed sources because selecting sources by the languages they declare
        only ever approximates the language their articles turn out to be in: a source declaring
        German and English survives a restriction to German, but its English articles do not.
        """
        return self._language_filter

    def restrict(
        self,
        source_types: Optional[Iterable[Type[URLSource]]] = None,
        languages: Optional[Iterable[str]] = None,
    ) -> "Publisher":
        """A view on this publisher covering only the sources matching the given restrictions.

        An empty or omitted argument does not restrict on that axis. Restrictions accumulate:
        restricting an already restricted publisher narrows it further, so that neither call can
        widen what the other one asked for. The view is a shallow copy, sharing the robots.txt
        and the parser with the publisher it was taken from, and is never modified afterwards.

        Args:
            source_types (Optional[Iterable[Type[URLSource]]]): Only keep sources of these types.
            languages (Optional[Iterable[str]]): Only keep sources covering at least one of these
                languages, and keep only articles turning out to be in one of them.

        Returns:
            Publisher: A view on the surviving sources.
        """
        view = copy.copy(self)
        view._sources = self._sources.filter(source_types=source_types, languages=languages)
        view._language_filter = _narrow_languages(self._language_filter, languages)
        return view


class PublisherGroup(type):
    def __new__(cls, name, bases, attributes):
        new = super().__new__(cls, name, bases, attributes)

        # set __name__ and __group__
        for attribute, value in attributes.items():
            if isinstance(value, Publisher):
                value.__name__ = attribute
                value.__group__ = new
                if default_language := attributes.get("default_language"):
                    for source in value.sources:
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
        include_deprecated_attributes: bool = False,
    ) -> List[Publisher]:
        if not (attributes or source_types or languages):
            raise ValueError("You have to define at least one search condition")
        if not attributes:
            attributes = []
        if not languages:
            languages = []
        if not source_types:
            source_types = []

        matched: List[Publisher] = []
        unique_attributes = set(attributes)
        for publisher in cls:
            if unique_attributes.issubset(
                set(publisher.parser().attributes().names)
                - (
                    set(
                        publisher.parser().attributes().deprecated.names if not include_deprecated_attributes else set()
                    )
                )
            ) and (publisher.supports(source_types=source_types, languages=languages)):
                matched.append(publisher.restrict(source_types=source_types, languages=languages))
        if not matched:
            warn("No publisher found matching the search criteria. Returning no publishers.")
        return matched
