import functools
import inspect
import re
from abc import ABC
from copy import copy
from datetime import date
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import lxml.html
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser.context import Precomputed, get_ld_content, get_meta_content
from fundus.parser.linked_data import LinkedDataMapping

logger = create_logger(__name__)


RegisteredFunctionT_co = TypeVar("RegisteredFunctionT_co", covariant=True, bound="RegisteredFunction")


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
        deprecated: Optional[date],
        default_factory: Optional[Callable[[], Any]],
    ):
        self.validate = validate
        self.deprecated = deprecated
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
    deprecated: Optional[date] = None,
    default_factory: Optional[Callable[[], Any]] = None,
):
    return _register(
        cls,
        factory=Attribute,
        priority=priority,
        validate=validate,
        deprecated=deprecated,
        default_factory=default_factory,
    )


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

    @property
    def deprecated(self) -> "AttributeCollection":
        return AttributeCollection(*[attr for attr in self.functions if attr.deprecated is not None])


class FunctionCollection(RegisteredFunctionCollection[Function]):
    pass


class BaseParser(ABC):
    VALID_UNTIL: date
    precomputed: Precomputed

    def __init__(self, timestamp: Optional[date] = None):
        def predicate(x: object) -> bool:
            if not isinstance(x, RegisteredFunction):
                return False
            if isinstance(x, Attribute):
                if timestamp is None or x.deprecated is None or x.deprecated > timestamp:
                    return True
                else:
                    return False
            return True

        predicated_members: List[Tuple[str, RegisteredFunction]] = inspect.getmembers(self, predicate=predicate)
        bound_registered_functions: List[RegisteredFunction] = [func for _, func in predicated_members]
        self._sorted_registered_functions = sorted(bound_registered_functions, key=lambda f: (f, f.__name__))

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "VALID_UNTIL" not in cls.__dict__:
            cls.VALID_UNTIL = date.max

    @classmethod
    def version(cls) -> str:
        return cls.__name__

    @classmethod
    def body_selectors(cls) -> Dict[str, Optional[XPath]]:
        """The version's body selectors, keyed 'summary' / 'subheadline' / 'paragraph'.

        These are the selectors a version feeds to ``extract_article_body_with_selector``;
        a value is None when the version does not declare the corresponding selector
        (or builds its body another way entirely). Public so external tooling (e.g. the
        review skill under skills/) does not have to reach into the private
        ``_*_selector`` attributes.

        The naming convention this relies on — a selector passed as ``<x>_selector`` lives on
        the class as ``_<x>_selector`` — is nothing but a convention, so it is enforced by
        ``tests/publishers/test_parser_coverage.py::TestPublisherParsers::test_body_selector_naming``
        until the selectors become declared class variables (see #958, which retires both).
        """
        return {
            "summary": getattr(cls, "_summary_selector", None),
            "subheadline": getattr(cls, "_subheadline_selector", None),
            "paragraph": getattr(cls, "_paragraph_selector", None),
        }

    @classmethod
    def _search_members(cls, obj_type: type) -> List[Tuple[str, Any]]:
        members = inspect.getmembers(cls, predicate=lambda x: isinstance(x, obj_type)) if obj_type else []
        return members

    @classmethod
    def attributes(cls, include_all: bool = False) -> AttributeCollection:
        # We exclude both __ld and __meta here to hide them from the autogenerated tables. We do so, because
        # we neither want them to appear in the attribute_guidelines nor the supported_publishers tables.
        attrs: List[Attribute] = [
            func for _, func in cls._search_members(Attribute) if include_all or func.__name__ not in ["__ld", "__meta"]
        ]
        return AttributeCollection(*attrs)

    @classmethod
    def functions(cls) -> FunctionCollection:
        funcs: List[Function] = [func for _, func in cls._search_members(Function)]
        return FunctionCollection(*funcs)

    @property
    def cache(self) -> Optional[Dict[str, Any]]:
        return self.precomputed.cache if self.precomputed else None

    @property
    def registered(self) -> RegisteredFunctionCollection[RegisteredFunction]:
        return RegisteredFunctionCollection(*self._sorted_registered_functions)

    @property
    def registered_attributes(self) -> AttributeCollection:
        return AttributeCollection(
            *[
                func
                for func in self._sorted_registered_functions
                if isinstance(func, Attribute) and func.__name__ not in ["__ld", "__meta"]
            ]
        )

    @property
    def registered_functions(self) -> FunctionCollection:
        return FunctionCollection(*[func for func in self._sorted_registered_functions if isinstance(func, Function)])

    def _base_setup(self, html: str) -> None:
        doc = lxml.html.document_fromstring(html)
        self.precomputed = Precomputed(html, doc, get_meta_content(doc), get_ld_content(doc))

    def parse(self, html: str, raise_on_error: bool = True) -> Dict[str, Any]:
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
                    if raise_on_error:
                        raise err
                    parsed_data[attribute_name] = func.__default__
                    logger.info(
                        f"Couldn't parse attribute {attribute_name!r} for "
                        f"{self.precomputed.meta.get('og:url')!r}: {err!r}"
                    )

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
