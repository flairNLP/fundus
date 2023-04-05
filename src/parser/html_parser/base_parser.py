import functools
import inspect
import json
import re
from abc import ABC
from copy import copy
from dataclasses import dataclass, field
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
)

import lxml.html
import more_itertools

from src.parser.html_parser.data import LinkedDataMapping
from src.parser.html_parser.utility import get_meta_content

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
            return f"bound {self.__class__.__name__} of {instance}: {self.__wrapped__} --> '{self.__name__}'"
        else:
            return f"registered {self.__class__.__name__}: {self.__wrapped__} --> '{self.__name__}'"


class Attribute(RegisteredFunction):
    def __init__(self, func: Callable[[object], Any], priority: Optional[int], supported: bool):
        self.supported = supported
        super(Attribute, self).__init__(func=func, priority=priority)


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


def attribute(cls=None, /, *, priority: Optional[int] = None, supported: bool = True):
    return _register(cls, factory=Attribute, priority=priority, supported=supported)


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

    def __eq__(self, other) -> bool:
        return self.functions == other.functions if isinstance(other, RegisteredFunctionCollection) else False


class AttributeCollection(RegisteredFunctionCollection[Attribute]):
    @property
    def supported(self) -> List[Attribute]:
        return [attr for attr in self.functions if attr.supported]

    @property
    def unsupported(self) -> List[Attribute]:
        return [attr for attr in self.functions if not attr.supported]


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
        attrs = [func for _, func in cls._search_members(Attribute) if func.__name__ not in ["__ld", "__meta"]]
        return AttributeCollection(*attrs)

    @classmethod
    def functions(cls) -> FunctionCollection:
        funcs = [func for _, func in cls._search_members(Function)]
        return FunctionCollection(*funcs)

    @property
    def cache(self) -> Optional[Dict[str, Any]]:
        return self.precomputed.cache if self.precomputed else None

    def _base_setup(self, html: str) -> None:
        doc = lxml.html.document_fromstring(html)
        ld_nodes = doc.xpath("//script[@type='application/ld+json']")
        lds = [json.loads(node.text_content()) for node in ld_nodes]
        collapsed_lds = more_itertools.collapse(lds, base_type=dict)
        self.precomputed = Precomputed(html, doc, get_meta_content(doc), LinkedDataMapping(collapsed_lds))

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
                    if error_handling == "catch":
                        parsed_data[attribute_name] = err
                    elif error_handling == "suppress" or error_handling == "raise":
                        raise err
                    else:
                        raise ValueError(f"Invalid value '{error_handling}' for parameter <error_handling>")

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
