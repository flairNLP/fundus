import inspect
from dataclasses import dataclass, field
from enum import Enum, EnumMeta, unique
from itertools import islice
from typing import Any, Dict, Iterator, List, Optional, Type

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


class PublisherEnumMeta(EnumMeta):
    def __str__(self) -> str:
        representation = f"Region {self.__name__!r} containing {len(self)} publisher(s):"
        publisher: str
        for publisher in self.__members__.values():
            representation += f"\n\t {publisher}"
        return representation


@unique
class PublisherEnum(Enum, metaclass=PublisherEnumMeta):
    def __new__(cls, *args, **kwargs):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, spec: PublisherSpec):
        if not isinstance(spec, PublisherSpec):
            raise ValueError("Your only allowed to generate 'PublisherEnum's from 'PublisherSpec")
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

    @classmethod
    def search(
        cls, attributes: Optional[List[str]] = None, source_types: Optional[List[Type[URLSource]]] = None
    ) -> List["PublisherEnum"]:
        if not (attributes or source_types):
            raise ValueError("You have to define at least one search condition")
        if not attributes:
            attributes = []
        matched = []
        unique_attributes = set(attributes)
        spec: PublisherEnum
        for spec in list(cls):
            if unique_attributes.issubset(spec.parser().attributes().names) and (
                spec.supports(source_types) if source_types else True
            ):
                matched.append(spec)
        return matched

    def __get__(self, instance, owner):
        return self


class PublisherCollectionMeta(type):
    """This class is the meta-class for creating Publisher Collections.

    Publishers used in the collection have to be of type PublisherEnum, e.g.

    >>> class PoliticalPublisher(PublisherEnum):
    >>>     ...
    >>>
    >>> class NewCollection(metaclass=PublisherCollectionMeta):
    >>>     political = PoliticalPublisher

    You can still use methods or non-PublisherEnum class attributes, e.g.

    >>> class NewCollection(metaclass=PublisherCollectionMeta):
    >>>     _id: int = 1
    >>>     political = PoliticalPublisher
    >>>
    >>>     @property
    >>>     def id(self) -> int:
    >>>         return self._id

    will work perfectly fine.
    """

    @staticmethod
    def _is_publisher_enum(obj: Any) -> bool:
        return inspect.isclass(obj) and issubclass(obj, PublisherEnum)

    def __new__(mcs, name, bases, attrs):
        included_enums: List[EnumMeta] = [value for value in attrs.values() if mcs._is_publisher_enum(value)]
        publisher_mapping: Dict[str, PublisherEnum] = {}
        for country_enum in included_enums:
            for publisher_enum in country_enum:  # type: ignore
                if existing := publisher_mapping.get(publisher_enum.name):
                    raise AttributeError(
                        f"Found duplicate publisher names in same collection {name!r}: "
                        f"{type(existing).__name__} -> {existing.name} and "
                        f"{type(publisher_enum).__name__} -> {publisher_enum.name}"
                    )
                publisher_mapping[publisher_enum.name] = publisher_enum
        return super().__new__(mcs, name, bases, attrs)

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

    def __iter__(cls) -> Iterator[PublisherEnum]:
        """This will iterate over all publishers included in the enums and not the enums itself.

        Returns:
            Iterator[PublisherEnum]: Iterator over publishers included in the enums.

        """
        for enum in cls.get_publisher_enum_mapping().values():
            yield from enum

    def __getitem__(self, name: str) -> PublisherEnum:
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
