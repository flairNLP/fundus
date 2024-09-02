import inspect
from textwrap import indent
from typing import Dict, Iterator, List, Optional, Type, Union

from robots import RobotFileParser

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, URLSource
from fundus.utils.iteration import iterate_all_subclasses


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
        request_header: Optional[Dict[str, str]] = None,
        deprecated: bool = False,
    ):
        """Initialization of a new Publisher object

        Args:
            name (str): Name of the publisher, as it would appear on the website
            domain (str): The domain of the publishers website
            parser (Type[ParserProxy]): Corresponding ParserProxy Object
            sources (List[URLSource]): List of sources for articles from the publishers
            query_parameter (Optional[Dict[str, str]]): Dictionary of query parameter: content to be appended to crawled URLs
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
        self.robots = RobotFileParser(
            self.domain + "robots.txt" if self.domain.endswith("/") else self.domain + "/robots.txt"
        )
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

        self.source_mapping = source_mapping

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

    def supports(self, source_types: List[Type[URLSource]]) -> bool:
        if not source_types:
            raise ValueError(f"Got empty value '{source_types}' for parameter <source_types>.")
        for source_type in source_types:
            if not inspect.isclass(source_type) or not issubclass(source_type, URLSource):
                raise TypeError(
                    f"Got unexpected type {source_type!r}. "
                    f"Allowed are {', '.join(repr(self.__name__) for self in iterate_all_subclasses(URLSource))}"
                )
        return all(bool(self.source_mapping.get(source_type)) for source_type in source_types)


class PublisherGroup(type):
    def __new__(cls, name, bases, attributes):
        new = super().__new__(cls, name, bases, attributes)

        # set __name__ and __group__
        for attribute, value in attributes.items():
            if isinstance(value, Publisher):
                value.__name__ = attribute
                value.__group__ = new

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
        cls, attributes: Optional[List[str]] = None, source_types: Optional[List[Type[URLSource]]] = None
    ) -> List[Publisher]:
        if not (attributes or source_types):
            raise ValueError("You have to define at least one search condition")
        if not attributes:
            attributes = []
        matched = []
        unique_attributes = set(attributes)
        spec: Publisher
        for publisher in cls:
            if unique_attributes.issubset(publisher.parser().attributes().names) and (
                publisher.supports(source_types) if source_types else True
            ):
                matched.append(publisher)
        return matched
