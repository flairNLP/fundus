import functools
import inspect
import itertools
import re
from abc import ABC
from copy import copy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import lxml.html

from fundus.logging import create_logger
from fundus.parser.data import LinkedDataMapping
from fundus.parser.utility import get_ld_content, get_meta_content

RegisteredFunctionT_co = TypeVar("RegisteredFunctionT_co", covariant=True, bound="RegisteredFunction")

logger = create_logger(__name__)


class RegisteredFunction(ABC):
    __wrapped__: Callable[[object], Any]
    __name__: str
    __func__: Callable[[object], Any]
    __self__: Optional["BaseParser"]

    # TODO: ensure uint for priority instead of int
    def __init__(self, func: Callable[[object], Any], priority: Optional[int]):
        self.__self__ = None
        self.__func__ = func
        self.__finite__: bool = False

        self.priority = priority

    def __get__(self, instance, owner):
        if instance and not self.__self__:
            method = copy(self)
            method.__self__ = instance
            method.__finite__ = True
            return method
        return self

    def __call__(self):
        if self.__self__ and hasattr(self.__self__, "precomputed"):
            return self.__func__(self.__self__)
        else:
            raise ValueError("You are not allowed to call attributes or functions outside the parse() method")

    def __lt__(self, other):
        if self.priority is None:
            return False
        elif other.priority is None:
            return True
        else:
            return self.priority < other.priority

    def __repr__(self):
        if instance := self.__self__:
            return f"bound {type(self).__name__} {self.__name__!r} of {instance}"
        else:
            return f"registered {type(self).__name__} {self.__name__!r}"


class Attribute(RegisteredFunction):
    def __init__(
        self,
        func: Callable[[object], Any],
        priority: Optional[int],
        validate: bool,
        default_factory: Optional[Callable[[], Any]],
    ):
        self.validate = validate
        self.default_factory = default_factory
        super(Attribute, self).__init__(func=func, priority=priority)

    @functools.cached_property
    def __default__(self):
        if self.default_factory is not None:
            return self.default_factory()

        annotation = self.__annotations__["return"]
        origin = get_origin(annotation)
        args = get_args(annotation)

        if not (origin or args):
            default = annotation()
        elif origin == Union:
            if type(None) in args:
                default = None
            else:
                raise NotImplementedError(f"Cannot determine default for {origin!r} with args {args!r}")
        elif isinstance(origin, type):
            default = origin()
        else:
            raise NotImplementedError(f"Unsupported origin {origin}")
        return default


class Function(RegisteredFunction):
    def __init__(self, func: Callable[[object], Any], priority: Optional[int]):
        super(Function, self).__init__(func=func, priority=priority)


def _register(cls, factory: Type[RegisteredFunction], **kwargs):
    def wrapper(func):
        return functools.update_wrapper(factory(func, **kwargs), func)

    # _register was called with parenthesis
    if cls is None:
        return wrapper

    # register was called without parenthesis
    return wrapper(cls)


def attribute(
    cls=None,
    /,
    *,
    priority: Optional[int] = None,
    validate: bool = True,
    default_factory: Optional[Callable[[], Any]] = None,
):
    return _register(cls, factory=Attribute, priority=priority, validate=validate, default_factory=default_factory)


def function(cls=None, /, *, priority: Optional[int] = None):
    return _register(cls, factory=Function, priority=priority)


class RegisteredFunctionCollection(Collection[RegisteredFunctionT_co]):
    def __init__(self, *functions: RegisteredFunctionT_co):
        self.functions = tuple(functions)

    @property
    def names(self) -> List[str]:
        return [func.__name__ for func in self.functions]

    def __len__(self) -> int:
        return len(self.functions)

    def __iter__(self) -> Iterator[RegisteredFunctionT_co]:
        return iter(self.functions)

    def __contains__(self, item) -> bool:
        return self.functions.__contains__(item)

    def __eq__(self, other: object) -> bool:
        return self.functions == other.functions if isinstance(other, RegisteredFunctionCollection) else False

    def __str__(self) -> str:
        return ", ".join(self.names)


class AttributeCollection(RegisteredFunctionCollection[Attribute]):
    @property
    def validated(self) -> "AttributeCollection":
        return AttributeCollection(*[attr for attr in self.functions if attr.validate])

    @property
    def unvalidated(self) -> "AttributeCollection":
        return AttributeCollection(*[attr for attr in self.functions if not attr.validate])


class FunctionCollection(RegisteredFunctionCollection[Function]):
    pass


@dataclass
class Precomputed:
    html: str
    doc: lxml.html.HtmlElement
    meta: Dict[str, str]
    ld: LinkedDataMapping
    cache: Dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    VALID_UNTIL: date = date.today()
    precomputed: Precomputed

    def __init__(self):
        predicate: Callable[[object], bool] = lambda x: isinstance(x, RegisteredFunction)
        predicated_members: List[Tuple[str, RegisteredFunction]] = inspect.getmembers(self, predicate=predicate)
        bound_registered_functions: List[RegisteredFunction] = [func for _, func in predicated_members]
        self._sorted_registered_functions = sorted(bound_registered_functions, key=lambda f: (f, f.__name__))

    @classmethod
    def _search_members(cls, obj_type: type) -> List[Tuple[str, Any]]:
        members = inspect.getmembers(cls, predicate=lambda x: isinstance(x, obj_type)) if obj_type else []
        return members

    @classmethod
    def attributes(cls) -> AttributeCollection:
        # We exclude both __ld and __meta here to hide them from the autogenerated tables. We do so, because
        # we neither want them to appear in the attribute_guidelines nor the supported_publishers tables.
        attrs: List[Attribute] = [
            func for _, func in cls._search_members(Attribute) if func.__name__ not in ["__ld", "__meta"]
        ]
        return AttributeCollection(*attrs)

    @classmethod
    def functions(cls) -> FunctionCollection:
        funcs: List[Function] = [func for _, func in cls._search_members(Function)]
        return FunctionCollection(*funcs)

    @property
    def cache(self) -> Optional[Dict[str, Any]]:
        return self.precomputed.cache if self.precomputed else None

    def _base_setup(self, html: str) -> None:
        doc = lxml.html.document_fromstring(html)
        self.precomputed = Precomputed(html, doc, get_meta_content(doc), get_ld_content(doc))

    def parse(self, html: str, error_handling: Literal["suppress", "catch", "raise"] = "raise") -> Dict[str, Any]:
        # wipe existing precomputed
        self._base_setup(html)

        parsed_data = {}

        for func in self._sorted_registered_functions:
            attribute_name = re.sub(r"^_{1,2}([^_]*_?)$", r"\g<1>", func.__name__)

            if isinstance(func, Function):
                func()

            elif isinstance(func, Attribute):
                try:
                    parsed_data[attribute_name] = func()
                except Exception as err:
                    if error_handling == "suppress":
                        parsed_data[attribute_name] = func.__default__
                        logger.info(
                            f"Couldn't parse attribute {attribute_name!r} for "
                            f"{self.precomputed.meta.get('og:url')!r}: {err}"
                        )
                    elif error_handling == "catch":
                        parsed_data[attribute_name] = err
                    elif error_handling == "raise":
                        raise err
                    else:
                        raise ValueError(f"Invalid value {error_handling!r} for parameter <error_handling>")

            else:
                raise TypeError(f"Invalid type for {func}. Only subclasses of 'RegisteredFunction' are allowed")

        return parsed_data

    def share(self, **kwargs):
        for key, value in kwargs.items():
            self.precomputed.cache[key] = value

    # base attribute section
    @attribute
    def __meta(self) -> Dict[str, Any]:
        return self.precomputed.meta

    @attribute
    def __ld(self) -> Optional[LinkedDataMapping]:
        return self.precomputed.ld

    @attribute
    def free_access(self) -> bool:
        if (isAccessibleForFree := self.precomputed.ld.bf_search("isAccessibleForFree")) is None:
            return True
        elif not isAccessibleForFree or isAccessibleForFree == "false" or isAccessibleForFree == "False":
            return False
        else:
            return True


class _ParserCache:
    def __init__(self, factory: Type[BaseParser]):
        self.factory: Type[BaseParser] = factory
        self.instance: Optional[BaseParser] = None

    def __call__(self) -> BaseParser:
        if not self.instance:
            self.instance = self.factory()
        return self.instance


class ParserProxy(ABC):
    def __init__(self):
        predicate: Callable[[object], bool] = lambda x: inspect.isclass(x) and issubclass(x, BaseParser)
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
        return parser_cache()

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
