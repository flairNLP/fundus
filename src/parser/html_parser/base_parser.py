import functools
import inspect
import json
from abc import ABC
from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Any, Literal, List, Union, Tuple, Type

import lxml.html

from src.parser.html_parser.utility import get_meta_content


class RegisteredFunction(ABC):
    __wrapped__: callable = None
    __func__: callable
    __self__: object
    __slots__ = ['__dict__', '__self__', '__func__', 'priority']

    # TODO: ensure uint for priority instead of int
    def __init__(self,
                 func: Callable,
                 priority: Optional[int] = None):

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

    def __call__(self, *args, **kwargs):
        return self.__func__(self.__self__, *args, *kwargs)

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

    def __init__(self,
                 func: Callable,
                 priority: Optional[int] = None):
        super(Attribute, self).__init__(func=func,
                                        priority=priority)


class Function(RegisteredFunction):

    def __init__(self,
                 func: Callable,
                 priority: Optional[int] = None):
        super(Function, self).__init__(func=func,
                                       priority=priority)


def _register(cls, factory: Type[RegisteredFunction], priority):
    def wrapper(func):
        return functools.update_wrapper(factory(func, priority), func)

    # _register was called with parenthesis
    if cls is None:
        return wrapper

    # register was called without parenthesis
    return wrapper(cls)


def register_attribute(cls=None, /, *, priority: Optional[int] = None):
    return _register(cls, factory=Attribute, priority=priority)


def register_function(cls=None, /, *, priority: Optional[int] = None):
    return _register(cls, factory=Function, priority=priority)


# noinspection PyPep8Naming
class LinkedData:
    __slots__ = ['_ld_by_type']

    def __init__(self, lds: List[Dict[str, any]]):
        self._ld_by_type: Dict[str, Union[List[Dict[str, any]], Dict[str, any]]] = defaultdict(list)
        for ld in lds:
            if ld_type := ld.get('@type'):
                self._ld_by_type[ld_type] = ld
            else:
                self._ld_by_type[ld_type].append(ld)

    @staticmethod
    def _property_names() -> List[str]:
        property_names = [p for p in dir(LinkedData) if isinstance(getattr(LinkedData, p), property)]
        property_names.remove('unsupported')
        return property_names

    @property
    def VideoObject(self) -> Dict[str, any]:
        return self._ld_by_type.get('VideoObject', {})

    @property
    def NewsArticle(self) -> Dict[str, any]:
        return self._ld_by_type.get('NewsArticle', {})

    @property
    def unsupported(self) -> Dict[str, any]:
        return {k: v for k, v in self._ld_by_type.items() if k not in self._property_names()}

    def get(self, key: str, default: any = None):
        for name, ld in self._ld_by_type.items():
            if not name:
                raise NotImplementedError("Currently this function does not support lds without types")
            elif value := ld.get(key):
                return value
        return default

    def __repr__(self):
        contains = [name for name in self._property_names() if getattr(self, name)]
        text = f"LD containing '{', '.join(contains)}'"
        if u := self.unsupported:
            tmp = f" and unsupported {', '.join(u.keys())}"
            text = text + tmp
        return text


@dataclass
class Precomputed:
    html: str = None
    doc: lxml.html.HtmlElement = None
    meta: Dict[str, Any] = field(default_factory=dict)
    ld: LinkedData = None
    cache: Dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):

    def __init__(self):
        self._shared_object_buffer: Dict[str, Any] = {}

        predicate: callable = lambda x: isinstance(x, RegisteredFunction)
        predicated_members: List[Tuple[str, RegisteredFunction]] = inspect.getmembers(self, predicate=predicate)
        bound_registered_functions: List[RegisteredFunction] = [func for _, func in predicated_members]
        self._sorted_registered_functions = sorted(bound_registered_functions, key=lambda f: (f, f.__name__))

        self.precomputed = Precomputed()

    @property
    def cache(self) -> Dict[str, Any]:
        return self.precomputed.cache

    @classmethod
    def _search_members(cls, obj_type: type) -> List[Tuple[str, Any]]:
        members = inspect.getmembers(cls, predicate=lambda x: isinstance(x, obj_type)) if obj_type else None
        return members

    @classmethod
    def attributes(cls) -> List[str]:
        return [func.__name__ for _, func in cls._search_members(Attribute)]

    def _base_setup(self, html: str) -> None:
        self.precomputed.html = html
        doc = lxml.html.fromstring(html)
        ld_nodes = doc.xpath("//script[@type='application/ld+json']")
        lds = [json.loads(node.text_content()) for node in ld_nodes]
        self.precomputed.doc = doc
        self.precomputed.ld = LinkedData(lds)
        self.precomputed.meta = get_meta_content(doc)

    def _wipe(self):
        self.precomputed = Precomputed()

    def parse(self, html: str,
              error_handling: Literal['suppress', 'catch', 'raise'] = 'raise') -> Optional[Dict[str, Any]]:

        # wipe existing precomputed
        self._wipe()
        self._base_setup(html)

        parsed_data = {}

        for func in self._sorted_registered_functions:

            if isinstance(func, Function):
                func()

            elif isinstance(func, Attribute):
                try:
                    parsed_data[func.__name__] = func()
                except Exception as err:
                    if error_handling == 'raise':
                        raise err
                    elif error_handling == 'catch':
                        parsed_data[func.__name__] = err
                    elif error_handling == 'suppress':
                        parsed_data[func.__name__] = None
                    else:
                        raise ValueError(f"Invalid value '{error_handling}' for parameter <error_handling>")

            else:
                raise TypeError(f"Invalid type for {func}. Only subclasses of 'RegisteredFunction' are allowed")

        return parsed_data

    def share(self, **kwargs):
        for key, value in kwargs.items():
            self.precomputed.cache[key] = value

    # base attribute section
    @register_attribute
    def meta(self) -> Dict[str, Any]:
        return self.precomputed.meta

    @register_attribute
    def ld(self) -> LinkedData:
        return self.precomputed.ld
