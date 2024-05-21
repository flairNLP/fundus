import inspect
from dataclasses import dataclass, field
from enum import Enum, EnumMeta, unique
from itertools import islice
from typing import Any, Dict, Iterator, List, Optional, Set, Type, Union

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, URLSource
from fundus.utils.iteration import iterate_all_subclasses


class Publisher(object):

    def __init__(
            self,
            name: str,
            domain: str,
            parser: Type[ParserProxy],
            sources: List[URLSource],
            query_parameter: Dict[str, str] = None,
            url_filter: Optional[URLFilter] = None,
            request_header: Dict[str, str] = None,
    ):
        if not (name and domain and parser and sources):
            raise ValueError("Failed to create Publisher. Name, Domain, Parser and Sources are mandatory")
        self.name = name
        self.parser = parser()
        self.domain = domain
        self.sources = sources
        self.query_parameter = query_parameter
        self.url_filter = url_filter
        self.request_header = request_header
        # we define the dict here manually instead of using default dict so that we can control
        # the order in which sources are proceeded.
        source_mapping: Dict[Type[URLSource], List[URLSource]] = {
            RSSFeed: [],
            NewsMap: [],
            Sitemap: [],
        }

        for url_source in self.sources:
            if not isinstance(url_source, URLSource):
                raise TypeError(
                    f"Unexpected type {type(url_source).__name__!r} as source for {self!r}. "
                    f"Allowed are {', '.join(repr(cls.__name__) for cls in iterate_all_subclasses(URLSource))}"
                )
            source_mapping[type(url_source)].append(url_source)

        self.source_mapping = source_mapping

    def __hash__(self):
        return hash(self.name)

    def __str__(self) -> str:
        return f"{self.name}"

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


# TODO: An Metaclass anpassen

class PublisherGroup(type):
    _length: int
    _contents: set

    def __new__(cls, *args, **kwargs):
        cls._contents = set(dir(cls)) - set(dir(PublisherGroup))
        cls._length = 0
        for element in cls._contents:
            if isinstance(publisher_group := getattr(cls, element), PublisherGroup):
                cls._length += len(publisher_group)
            elif isinstance(getattr(cls, element), Publisher):
                cls._length += 1
            else:
                raise AttributeError(f"Element {element} of type {type(element)} is not supported")
        testing_set: Set[Publisher] = set()
        # TODO: iteration
        for element in cls._contents:
            if element in testing_set:
                raise AttributeError(f"Element {element} is already contained within this publisher group")
            else:
                testing_set.add(element)
        return super().__new__(cls, *args, **kwargs)

    def get_publisher_enum_mapping(self) -> Dict[str, Publisher]:
        return {publisher.name: publisher for publisher in self}

    def __contains__(self, __x: object) -> bool:
        return __x in self._contents

    def __iter__(self) -> Iterator[Publisher]:
        """This will iterate over all publishers included in the group and its subgroups.

        Returns:
            Iterator[Publisher]: Iterator over publishers included in the group and its subgroups.

        """
        for element_name in self._contents:
            if isinstance(element := getattr(self, element_name), Publisher):
                yield element
            elif isinstance(element, PublisherGroup):
                yield from element
            else:
                raise AttributeError(f"Element {element} of invalid type {type(element)}")

    def __getitem__(self, name: str) -> Publisher:
        """Get a publisher from the collection by name represented as string.

        Args:
            name: A string referencing the publisher in the corresponding enum.

        Returns:
            PublisherEnum: The corresponding publisher.

        """
        if name in self._contents and isinstance(publisher := getattr(self, name), Publisher):
            return publisher
        for element in self._contents:
            if isinstance(publisher_group := getattr(self, element), PublisherGroup):
                try:
                    return publisher_group[name]
                except KeyError:
                    pass
        raise KeyError(f"Publisher {name!r} not present in {self.__name__}")

    def __len__(self) -> int:
        """The number of publishers included in the group.

        Returns:
            int: The number of publishers.
        """
        return self._length

    def __str__(self) -> str:
        representation = f"The {type(self).__name__!r} consists of {len(self)} publishers:"
        publisher: str
        group: str
        for element_name in self._contents:
            element = getattr(self, element_name)
            if isinstance(element, Publisher):
                representation += f"\t{str(element)}\n"
            elif isinstance(element, PublisherGroup):
                representation += f"\n\t {type(element).__name__}:"
                for publisher in islice(element, 0, 5):
                    representation += f"\n\t\t {publisher}"
            if len(element) > 5:
                representation += f"\n\t\t ..."
        return representation

    def search(
            self, attributes: Optional[List[str]] = None, source_types: Optional[List[Type[URLSource]]] = None
    ) -> List[Publisher]:
        if not (attributes or source_types):
            raise ValueError("You have to define at least one search condition")
        if not attributes:
            attributes = []
        matched = []
        unique_attributes = set(attributes)
        spec: Publisher
        for publisher in self:
            if unique_attributes.issubset(publisher.parser().attributes().names) and (
                    publisher.supports(source_types) if source_types else True
            ):
                matched.append(publisher)
        return matched
