import inspect
from dataclasses import dataclass, field
from enum import Enum, EnumMeta, unique
from typing import Any, Dict, Iterator, List, Optional, Type

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import UrlFilter
from fundus.scraping.source import NewsMap, RSSFeed, Sitemap, Source, URLSource
from fundus.utils.iteration import iterate_all_subclasses


@dataclass(frozen=True)
class PublisherSpec:
    domain: str
    parser: Type[ParserProxy]
    url_filter: Optional[UrlFilter] = field(default=None)
    sources: List[URLSource] = field(default_factory=list)

    def __post_init__(self):
        if not self.sources:
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
        self.parser = spec.parser()

        # we define the dict here manually instead of using default dict so that we can control
        # the order in which sources are proceeded.
        source_mapping: Dict[str, List[Source]] = {
            RSSFeed.__name__: [],
            NewsMap.__name__: [],
            Sitemap.__name__: [],
        }

        for url_source in spec.sources:
            if not isinstance(url_source, URLSource):
                raise TypeError(
                    f"Unexpected type {type(url_source).__name__} as source for {self.name}. "
                    f"Only {type(RSSFeed).__name__}, {type(NewsMap).__name__} and {type(Sitemap).__name__} "
                    f"are allowed as sources."
                )
            source: Source = Source(url_source=url_source, publisher=self.name, url_filter=spec.url_filter)
            source_mapping[type(url_source).__name__].append(source)

        self.source_mapping = source_mapping

    def supports(self, source_types: Optional[List[Type[URLSource]]]) -> bool:
        if source_types is None:
            return True
        else:
            if not isinstance(source_types, list):
                raise TypeError(f"Got unexpected type {type(source_types)}. Expected <class list>")
            for source_type in source_types:
                if not inspect.isclass(source_type):
                    raise TypeError(
                        f"Got unexpected type {type(source_type)}. "
                        f"Allowed are '{', '.join(cls.__name__ for cls in iterate_all_subclasses(URLSource))}'"
                    )
                elif not issubclass(source_type, URLSource):
                    raise TypeError(
                        f"Got unexpected type {source_type}. "
                        f"Allowed are '{', '.join(cls.__name__ for cls in iterate_all_subclasses(URLSource))}'"
                    )
            return all(bool(self.source_mapping.get(source_type.__name__)) for source_type in source_types)

    @classmethod
    def search(
        cls, attributes: Optional[List[str]] = None, source_types: Optional[List[Type[URLSource]]] = None
    ) -> List["PublisherEnum"]:
        assert attributes or source_types, "You have to define at least one search condition"
        if not attributes:
            attributes = []
        matched = []
        unique_attributes = set(attributes)
        spec: PublisherEnum
        for spec in list(cls):
            if unique_attributes.issubset(spec.parser().attributes().names) and spec.supports(source_types):
                matched.append(spec)
        return matched

    def __get__(self, instance, owner):
        return self


class PublisherCollectionMeta(type):
    def __new__(mcs, name, bases, attrs):
        included_enums: List[EnumMeta] = [value for value in attrs.values() if isinstance(value, EnumMeta)]
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

    @property
    def _members(cls) -> Dict[str, Any]:
        return {name: obj for name, obj in cls.__dict__.items() if "__" not in name}

    def __contains__(cls, __x: object) -> bool:
        return __x in cls._members.values()

    def __iter__(cls) -> Iterator[PublisherEnum]:
        for coll in cls._members.values():
            yield from coll

    def __getitem__(self, name: str) -> PublisherEnum:
        for publisher_enum in self:
            if publisher_enum.name == name:
                return publisher_enum
        raise KeyError(f"Publisher '{name}' not present in {self.__name__}")

    def __len__(cls) -> int:
        return len(cls._members)
