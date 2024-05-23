import inspect
from itertools import islice
from typing import Dict, Iterator, List, Optional, Type, overload, Union

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
        query_parameter: Optional[Dict[str, str]] = None,
        url_filter: Optional[URLFilter] = None,
        request_header: Optional[Dict[str, str]] = None,
    ):
        """
        Initialization of a new Publisher object

        @param name: Name of the publisher, as it would appear on the website
        @param domain: The domain of the publishers website
        @param parser: Corresponding ParserProxy Object
        @param sources: List of sources for articles from the publishers
        @param query_parameter: Dictionary of query parameter: content to be appended to crawled URLs
        @param url_filter: Regex filter to apply determining URLs to be skipped
        @param request_header: Request header to be used for the GET-request
        """
        if not (name and domain and parser and sources):
            raise ValueError("Failed to create Publisher. Name, Domain, Parser and Sources are mandatory")
        self.name = name
        self.parser = parser()
        self.domain = domain
        self.sources = sources
        self.query_parameter = query_parameter
        self.url_filter = url_filter
        self.request_header = request_header
        self.contained_in: Optional[str] = None
        # This variable has been chosed for backwards compatibility, where publisher_name used to be the name of the
        # publisher in the PublisherEnum
        self.publisher_name: Optional[str] = None
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


class PublisherGroup(type):
    _length: int
    _contents: set[str]

    def __hash__(self):
        return hash(self.__name__)

    def __new__(cls, *args, **kwargs):
        created_type = super().__new__(cls, *args, **kwargs)
        attributes = dir(created_type)
        attributes.remove("__weakref__")
        created_type._contents = set(attributes) - set(dir(PublisherGroup))
        created_type._length = 0
        for element in created_type._contents:
            if isinstance(publisher_group := getattr(created_type, element), PublisherGroup):
                created_type._length += len(publisher_group)
            elif isinstance(getattr(created_type, element), Publisher):
                created_type._length += 1
            else:
                raise ValueError(f"Element {element} of type {type(element)} is not supported")
        created_type._recursive_contents = set()
        for element in created_type._contents:
            attribute = getattr(created_type, element)
            if attribute in created_type._recursive_contents:
                raise AttributeError(f"The element {element} of type {type(attribute)} is already contained within this publisher group")
            if isinstance(attribute, Publisher):
                attribute.contained_in = created_type.__name__.lower()
                attribute.publisher_name = element
            elif isinstance(attribute, PublisherGroup):
                if created_type._contents & attribute._contents:
                    raise AttributeError(f"One or more publishers within {attribute} are already contained within this publisher group")
            created_type._recursive_contents.add(attribute)
        return created_type

    def get_publishers_mapping(self) -> Dict[str, Publisher]:
        return {publisher.name: publisher for publisher in self}

    def get_subgroup_mapping(self) -> Dict[str, "PublisherGroup"]:
        return {
            element: publisher_group
            for element in self._contents
            if isinstance((publisher_group := getattr(self, element)), PublisherGroup)
        }

    def __contains__(self, __x: Union[str, Publisher, "PublisherGroup"]) -> bool:
        if isinstance(__x, PublisherGroup):
            search_string = __x.__name__.lower()
        elif isinstance(__x, Publisher):
            search_string = __x.publisher_name
        else:
            search_string = __x
        if search_string in self._contents:
            return True
        for element in self._contents:
            if isinstance(attribute := getattr(self, element), PublisherGroup):
                if search_string in attribute:
                    return True
        return False


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
            Publisher: The corresponding publisher.

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
