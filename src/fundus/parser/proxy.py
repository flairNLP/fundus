import inspect
import itertools
from abc import ABC
from datetime import date, datetime
from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Type,
    Union,
)

from fundus.parser.base import AttributeCollection, BaseParser, FunctionCollection


class _ParserCache:
    def __init__(self, factory: Type[BaseParser]):
        self.factory: Type[BaseParser] = factory
        self._instances: Dict[Optional[date], BaseParser] = {}
        deprecated_dates = sorted(
            [attr.deprecated for attr in self.factory.attributes() if attr.deprecated is not None]
        )
        self._deprecation_timeframes: List[date] = deprecated_dates

    def __call__(self, timestamp: Optional[date] = None) -> BaseParser:
        effective_timestamp: Optional[date] = None
        if timestamp:
            for timeframe_date in reversed(self._deprecation_timeframes):
                if timeframe_date <= timestamp:
                    effective_timestamp = timeframe_date
                    break
        if effective_timestamp not in self._instances:
            self._instances[effective_timestamp] = self.factory(timestamp=effective_timestamp)

        return self._instances[effective_timestamp]


class ParserProxy(ABC):
    def __init__(self):
        def predicate(x: object) -> bool:
            return inspect.isclass(x) and issubclass(x, BaseParser)

        included_parsers: List[Type[BaseParser]] = [
            parser for name, parser in inspect.getmembers(type(self), predicate=predicate)
        ]

        if not included_parsers:
            raise ValueError(
                f"<class {type(self).__name__}> consists of no parser-versions. "
                f"To include versions add subclasses of <class {BaseParser.__name__}> to the class definition."
            )

        mapping: Dict[date, _ParserCache] = {}
        for versioned_parser in sorted(included_parsers, key=lambda parser: parser.VALID_UNTIL):
            validation_date: date
            if prev := mapping.get(validation_date := versioned_parser.VALID_UNTIL):  # type: ignore
                raise ValueError(
                    f"Found versions {prev.factory.__name__!r} and {versioned_parser.__name__!r} of "
                    f"{str(self)!r} with same validation date.\nMake sure you use class attribute VALID_UNTIL "
                    f"of <class {BaseParser.__name__}> to set validation dates for legacy versions."
                )
            mapping[validation_date] = _ParserCache(versioned_parser)
        self._parser_mapping = mapping

    def __call__(self, crawl_date: Optional[Union[datetime, date]] = None) -> BaseParser:
        if crawl_date is None:
            return self._get_latest_cache()()

        parsed_date = crawl_date.date() if isinstance(crawl_date, datetime) else crawl_date
        parser_cache: _ParserCache
        try:
            _, parser_cache = next(itertools.dropwhile(lambda x: x[0] < parsed_date, self._parser_mapping.items()))
        except StopIteration:
            raise ValueError(
                f"Couldn't find a fitting parser valid at date {parsed_date}. "
                f"Last valid date is {self._get_latest_cache()().VALID_UNTIL}"
            )
        return parser_cache(parsed_date)

    def __iter__(self) -> Iterator[Type[BaseParser]]:
        """Iterates over all included parser versions with the latest being first.

        Returns:
            Iterator over included parser versions
        """
        return (cache.factory for cache in reversed(self._parser_mapping.values()))

    def __len__(self) -> int:
        return len(self._parser_mapping)

    def __bool__(self) -> bool:
        return bool(self._parser_mapping)

    def __eq__(self, other: object) -> bool:
        """Two proxies are equal iff they are instances of the same ParserProxy subclass.

        A proxy carries no instance state beyond the versions collected from its own class
        definition, so the type determines the value. Without this, proxies fall back to
        identity comparison and two freshly instantiated proxies of the same class -- as
        held by two value-equal Publishers -- never compare equal.
        """
        if not isinstance(other, ParserProxy):
            return NotImplemented
        return type(self) is type(other)

    def __hash__(self) -> int:
        return hash(type(self))

    def __str__(self) -> str:
        return f"<{ParserProxy.__name__} {type(self).__name__}>"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__} including versions "
            f"{', '.join([cache.factory.__name__ for cache in self._parser_mapping.values()])!r}"
            if self._parser_mapping
            else f"Empty {type(self).__name__}"
        )

    @property
    def attribute_mapping(self) -> Dict[Type[BaseParser], AttributeCollection]:
        return {versioned_parser: versioned_parser.attributes() for versioned_parser in self}

    @property
    def function_mapping(self) -> Dict[Type[BaseParser], FunctionCollection]:
        return {versioned_parser: versioned_parser.functions() for versioned_parser in self}

    def _get_latest_cache(self) -> _ParserCache:
        return list(self._parser_mapping.values())[-1]

    @property
    def latest_version(self) -> Type[BaseParser]:
        return self._get_latest_cache().factory

    def versions_covering(self, start: date, end: date) -> Iterator[Type[BaseParser]]:
        """Iterates over the versions used to parse articles crawled between <start> and <end>.

        A version is valid from the day after its predecessor's VALID_UNTIL up to and including its
        own, so it takes part in the range as soon as those two spans overlap. Versions are yielded
        oldest first.

        Args:
            start: The first day of the range, inclusive.
            end: The last day of the range, inclusive.

        Returns:
            Iterator over the parser versions covering part of the range.
        """
        previous_valid_until = date.min
        for valid_until, cache in self._parser_mapping.items():
            if valid_until >= start and previous_valid_until < end:
                yield cache.factory
            previous_valid_until = valid_until
