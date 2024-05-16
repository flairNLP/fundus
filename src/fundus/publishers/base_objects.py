import inspect
from dataclasses import dataclass, field
from enum import Enum, EnumMeta, unique
from itertools import islice
from typing import Any, Dict, Iterator, List, Optional, Type, Union, Self

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, URLSource
from fundus.utils.iteration import iterate_all_subclasses


@dataclass(frozen=True)
class PublisherSpec:
    name: str
    domain: str
    parser: Type[ParserProxy]
    sources: List[URLSource]
    query_parameter: Dict[str, str] = field(default_factory=dict)
    url_filter: Optional[URLFilter] = field(default=None)
    request_header: Dict[str, str] = field(default_factory=dict)

# TODO: string representation of everything


@unique
class Publisher(object):
    def __init__(self, spec: PublisherSpec):
        if not isinstance(spec, PublisherSpec):
            raise ValueError("You're only allowed to generate a 'Publisher' from 'PublisherSpec")
        self.domain = spec.domain
        self.parser = spec.parser()
        self.publisher_name = spec.name
        self.query_parameter = spec.query_parameter
        self.url_filter = spec.url_filter
        self.request_header = spec.request_header
        # we define the dict here manually instead of using default dict so that we can control
        # the order in which sources are proceeded.
        source_mapping: Dict[Type[URLSource], List[URLSource]] = {
            RSSFeed: [],
            NewsMap: [],
            Sitemap: [],
        }
        for url_source in spec.sources:
            if not isinstance(url_source, URLSource):
                raise TypeError(
                    f"Unexpected type {type(url_source).__name__!r} as source for {self!r}. "
                    f"Allowed are {', '.join(repr(cls.__name__) for cls in iterate_all_subclasses(URLSource))}"
                )
            source_mapping[type(url_source)].append(url_source)
        self.source_mapping = source_mapping

    def __str__(self) -> str:
        return f"{self.publisher_name}"

    def supports(self, source_types: List[Type[URLSource]]) -> bool:
        if not source_types:
            raise ValueError(f"Got empty value '{source_types}' for parameter <source_types>.")
        for source_type in source_types:
            if not inspect.isclass(source_type) or not issubclass(source_type, URLSource):
                raise TypeError(
                    f"Got unexpected type {source_type!r}. "
                    f"Allowed are {', '.join(repr(cls.__name__) for cls in iterate_all_subclasses(URLSource))}"
                )
        return all(bool(self.source_mapping.get(source_type)) for source_type in source_types)


def search(
        attributes: Optional[List[str]] = None, source_types: Optional[List[Type[URLSource]]] = None
) -> List[Publisher]:
    if not (attributes or source_types):
        raise ValueError("You have to define at least one search condition")
    if not attributes:
        attributes = []
    matched = []
    unique_attributes = set(attributes)
    spec: Publisher
    for element in :
        if unique_attributes.issubset(spec.parser().attributes().names) and (
                spec.supports(source_types) if source_types else True
        ):
            matched.append(spec)
    return matched


class PublisherGroup(object):

    # TODO: Duplicate Testing

    __members__: Union[List[Publisher], List[Self]] = list()

    def get_publisher_enum_mapping(cls) -> Dict[str, EnumMeta]:
        """Returns all PublisherEnums included in the publisher collection as dictionary.

        E.g.

        >>> from fundus.publishers.at import AT
        >>> from fundus.publishers.de import DE
        >>> class PublisherCollection(metaclass=PublisherCollectionMeta):
        >>>     de: PublisherEnum = DE
        >>>     at: PublisherEnum = AT
        >>>     ...
        >>> print(PublisherCollection.get_publisher_enum_mapping())

        will print the following:

        {'de': <enum 'DE'>, 'at': <enum 'AT'>, ...}

        Returns:
            Dict[str, EnumMeta]: A dictionary mapping 'attribute_name -> enum' for all PublisherEnums
            in the same order as they were defined in the collection.

        """
        return {name: value for name, value in cls.__dict__.items() if cls._is_publisher_enum(value)}

    def __contains__(cls, __x: object) -> bool:
        return __x in cls.get_publisher_enum_mapping().values()

    def __iter__(cls) -> Iterator[Publisher]:
        """This will iterate over all publishers included in the enums and not the enums itself.

        Returns:
            Iterator[PublisherEnum]: Iterator over publishers included in the enums.

        """
        for enum in cls.get_publisher_enum_mapping().values():
            yield from enum

    def __getitem__(self, name: str) -> Publisher:
        """Get a publisher from the collection by name represented as string.

        Args:
            name: A string referencing the publisher in the corresponding enum.

        Returns:
            PublisherEnum: The corresponding publisher.

        """
        for publisher_enum in self:
            if publisher_enum.name == name:
                return publisher_enum
        raise KeyError(f"Publisher {name!r} not present in {self.__name__}")

    def __len__(cls) -> int:
        """The number of publishers included in the collection.

        Returns:
            int: The number of publishers.
        """
        return len(list(iter(cls)))

    def __str__(self) -> str:
        enum_mapping = self.get_publisher_enum_mapping()
        enum_mapping_keys = enum_mapping.keys()
        representation = (
            f"The {self.__name__!r} consists of {len(self)} publishers from {len(enum_mapping_keys)} , including:"
        )
        publisher: str
        country: str
        for country in enum_mapping_keys:
            representation += f"\n\t {country}:"
            for publisher in islice(enum_mapping[country], 0, 5):
                representation += f"\n\t\t {publisher}"
            if len(enum_mapping[country]) > 5:
                representation += f"\n\t\t ..."
        return representation
