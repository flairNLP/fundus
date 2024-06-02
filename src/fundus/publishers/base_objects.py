import inspect
from itertools import islice
from typing import Dict, Iterator, List, Optional, Set, Tuple, Type, Union, overload

from fundus.parser.base_parser import ParserProxy
from fundus.scraping.filter import URLFilter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, URLSource
from fundus.utils.iteration import iterate_all_subclasses


class Publisher:
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
        self.publisher_name = name
        self.parser = parser()
        self.domain = domain
        self.query_parameter = query_parameter
        self.url_filter = url_filter
        self.request_header = request_header
        # This variable has been chosen for backwards compatibility, where name used to be the name of the
        # publisher in the PublisherEnum
        self.name: Optional[str] = None
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

    def __hash__(self):
        return hash(self.publisher_name)

    def __str__(self) -> str:
        return f"{self.publisher_name}"

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
    def __hash__(cls):
        return hash(cls.__name__)

    def __new__(cls, name, bases, attributes):
        created_type = super().__new__(cls, name, bases, attributes)
        created_type.contents = set(attributes) - set(dir(PublisherGroup))
        testing_set = set()
        for element in created_type.contents:
            attribute = getattr(created_type, element)
            if attribute in testing_set:
                raise AttributeError(
                    f"The element {element} of type {type(attribute)} is already contained within this publisher group"
                )
            if isinstance(attribute, Publisher):
                attribute.name = element
            elif isinstance(attribute, PublisherGroup):
                if created_type._contents & attribute._contents:
                    raise AttributeError(
                        f"One or more publishers within {attribute} are already contained within this publisher group"
                    )
            else:
                raise ValueError(
                    f"Attribute of type {type(attribute)} is not allowd and should be Publisher or PublisherGroup"
                )
            testing_set.add(attribute)
        return created_type

    def _get_contents(cls):
        return cls._contents

    def _set_contents(cls, value):
        cls._contents = value

    contents = property(
        fget=_get_contents,
        fset=_set_contents,
        doc="Set containing the names of all direct children of this publisher group",
    )

    def get_publisher_mapping(cls) -> Dict[str, Publisher]:
        return {publisher.name: publisher for publisher in cls if publisher.name is not None}

    def get_subgroup_mapping(cls) -> Dict[str, "PublisherGroup"]:
        return {
            element: publisher_group
            for element in cls.contents
            if isinstance((publisher_group := getattr(cls, element)), PublisherGroup)
        }

    def __contains__(cls, __x: Union[str, Publisher, "PublisherGroup"]) -> bool:
        if isinstance(__x, PublisherGroup):
            search_string = __x.__name__.lower()
        elif isinstance(__x, Publisher):
            if __x.name:
                search_string = __x.name
            else:
                return False
        else:
            search_string = __x
        if search_string in cls.contents:
            return True
        for element in cls.contents:
            if isinstance(attribute := getattr(cls, element), PublisherGroup):
                if search_string in attribute:
                    return True
        return False

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

    def parent_iterator(cls) -> Iterator[Tuple[Publisher, "PublisherGroup"]]:
        for attribute in cls.__dict__.values():
            if isinstance(attribute, Publisher):
                yield attribute, cls
            elif isinstance(attribute, PublisherGroup):
                yield from attribute.parent_iterator()

    def __getitem__(cls, name: str) -> Publisher:
        """Get a publisher from the collection by name represented as string.

        Args:
            name: A string referencing the publisher in the corresponding enum.

        Returns:
            Publisher: The corresponding publisher.^

        """
        if (publisher := cls.get_publisher_mapping().get(name)) is None:
            raise KeyError(f"Publisher {name!r} not present in {cls.__name__}")
        return publisher

    def __len__(cls) -> int:
        """The number of publishers included in the group.

        Returns:
            int: The number of publishers.
        """
        return len(list(cls.__iter__()))

    def __str__(cls) -> str:
        representation = f"The {cls.__name__!r} PublisherGroup consists of {len(cls)} publishers:"
        for element_name in cls.contents:
            element = getattr(cls, element_name)
            if isinstance(element, Publisher):
                representation += f"\n\t{str(element)}"
            elif isinstance(element, PublisherGroup):
                representation += f"\n\t {element.__name__}:"
                for publisher in islice(element, 0, 5):
                    representation += f"\n\t\t {publisher}"
                if len(element) > 5:
                    representation += f"\n\t\t ..."
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
