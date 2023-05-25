import inspect
from dataclasses import dataclass, field
from enum import Enum, EnumMeta, unique
from typing import Any, Dict, Iterator, List, Optional, Type

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import UrlFilter


@dataclass(frozen=True)
class PublisherSpec:
    name: str
    domain: str
    parser: Type[ParserProxy]
    rss_feeds: List[str] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)
    url_filter: Optional[UrlFilter] = field(default=None)
    news_map: Optional[str] = field(default=None)

    def __post_init__(self):
        if not (self.rss_feeds or self.sitemaps or self.news_map):
            raise ValueError("Publishers must at least define either an rss-feed, sitemap or news_map to crawl")


@unique
class PublisherEnum(Enum):
    def __new__(cls, *args, **kwargs):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, spec: PublisherSpec):
        if not isinstance(spec, PublisherSpec):
            raise ValueError("Your only allowed to generate 'PublisherEnum's from 'PublisherSpec")
        self.domain = spec.domain
        self.rss_feeds = spec.rss_feeds
        self.sitemaps = spec.sitemaps
        self.news_map = spec.news_map
        self.parser = spec.parser()
        self.url_filter = spec.url_filter
        self.publisher_name = spec.name

    def supports(self, source_type: Optional[str]) -> bool:
        if source_type == "rss":
            return bool(self.rss_feeds)
        elif source_type == "sitemap":
            return bool(self.sitemaps)
        elif source_type == "news":
            return bool(self.news_map)
        elif source_type is None:
            return True
        else:
            raise ValueError(f"Unsupported value {source_type} for parameter <source_type>")

    @classmethod
    def search(cls, attrs: Optional[List[str]] = None, source_type: Optional[str] = None) -> List["PublisherEnum"]:
        assert attrs or source_type, "You have to define at least one search condition"
        if not attrs:
            attrs = []
        matched = []
        attrs_set = set(attrs)
        spec: PublisherEnum
        for spec in list(cls):
            if attrs_set.issubset(spec.parser().attributes().names) and spec.supports(source_type):
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
                        f"Found duplicate publisher names in same collection '{name}'. "
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
        raise KeyError(f"Publisher '{name}' not present in {self.__name__}")

    def __len__(cls) -> int:
        """The number of publishers included in the collection.

        Returns:
            int: The number of publishers.
        """
        return len(list(iter(cls)))
