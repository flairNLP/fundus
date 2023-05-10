from dataclasses import dataclass, field
from enum import Enum, EnumMeta, unique
from typing import Any, Dict, Iterator, List, Optional, Type

from fundus.parser.base_parser import ParserProxy


@dataclass(frozen=True)
class PublisherSpec:
    domain: str
    parser: Type[ParserProxy]
    rss_feeds: List[str] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)
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
