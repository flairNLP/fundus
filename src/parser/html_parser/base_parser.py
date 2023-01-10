import functools
import inspect
import json
import re
from abc import ABC
from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Any, Literal, List, Union

import lxml.html

from src.parser.html_parser.utility import get_meta_content


class RegisteredFunction:
    __wrapped__: callable = None
    __func__: callable
    __self__: object
    __slots__ = ['__dict__', '__self__', '__func__', 'flow_type', 'priority']

    # TODO: ensure uint for priority instead of int
    def __init__(self,
                 func: Callable,
                 flow_type: str,
                 priority: Optional[int] = None):

        self.__self__ = None
        self.__func__ = func
        self.__finite__: bool = False

        self.flow_type = flow_type
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
            return f"bound registered {self.flow_type} of {instance}: {self.__wrapped__} --> '{self.__name__}'"
        else:
            return f"registered {self.flow_type}: {self.__wrapped__} --> '{self.__name__}'"


def _register(cls, flow_type: Literal['attribute', 'function', 'filter'], priority):
    def wrapper(func):
        return functools.update_wrapper(RegisteredFunction(func, flow_type, priority), func)

    # _register was called with parenthesis
    if cls is None:
        return wrapper

    # register was called without parenthesis
    return wrapper(cls)


# TODO: Should 'registered_property' act like a property? and if so, implement it with a property wrapper or as __get__
#   in 'RegisteredFunction' d
def register_attribute(cls=None, /, *, priority: int = None):
    return _register(cls, flow_type='attribute', priority=priority)


def register_function(cls=None, /, *, priority: int = None):
    return _register(cls, flow_type='function', priority=priority)


def register_filter(cls=None, /, *, priority: int = None):
    return _register(cls, flow_type='filter', priority=priority)


class LinkedData:
    __slots__ = ['_ld_by_type', '__dict__']

    def __init__(self, lds: List[Dict[str, any]]):
        self._ld_by_type: Dict[str, Union[List[Dict[str, any]], Dict[str, any]]] = defaultdict(list)
        for ld in lds:
            if ld_type := ld.get('@type'):
                self._ld_by_type[ld_type] = ld
            else:
                self._ld_by_type[ld_type].append(ld)

        for name, ld in sorted(self._ld_by_type.items(), key=lambda t: t[0]):
            self.__dict__[name] = ld

        self._contains = [ld_type for ld_type in self._ld_by_type.keys() if ld_type is not None]

    def get(self, key: str, default: any = None):
        """
        This function acts like get() on pythons Mapping type with the difference that this method will
        iterate through all found ld types and return the first value where <key> matches. If no match occurs,
        <default> will be returned.

        If there is a ld without a type, thins methode will raise a NotImplementedError

        :param key: The key to search vor
        :param default: The returned default if <key> is not found, default: None
        :return:
        """
        for name, ld in sorted(self._ld_by_type.items(), key=lambda t: t[0]):
            if not name:
                raise NotImplementedError("Currently this function does not support lds without types")
            elif value := ld.get(key):
                return value
        return default

    def __repr__(self):
        return f"LD containing '{', '.join(self._contains)}'"


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

        self._registered_functions = [func for _, func in
                                      inspect.getmembers(self, predicate=lambda x: isinstance(x, RegisteredFunction))]

        self.precomputed = Precomputed()

    @property
    def cache(self) -> Dict[str, Any]:
        return self.precomputed.cache

    # TODO: once we have python 3.11 use getmember_static these properties
    @classmethod
    def registered_functions(cls) -> List[RegisteredFunction]:
        return [func for _, func in
                inspect.getmembers(cls, predicate=lambda x: isinstance(x, RegisteredFunction))]

    @classmethod
    def attributes(cls):
        return [func.__name__ for func in cls.registered_functions()]

    def _base_setup(self):
        content = self.precomputed.html
        doc = lxml.html.fromstring(content)
        ld_nodes = doc.xpath("//script[@type='application/ld+json']")
        lds = [json.loads(node.text_content()) for node in ld_nodes]
        self.precomputed.doc = doc
        self.precomputed.ld = LinkedData(lds)
        self.precomputed.meta = get_meta_content(doc) or {}

    def parse(self, html: str,
              error_handling: Literal['suppress', 'catch', 'raise'] = 'raise') -> Optional[Dict[str, Any]]:

        # wipe existing precomputed
        self._wipe()
        self.precomputed.html = html
        self._base_setup()
        article_cache = {}

        for func in sorted(self._registered_functions):

            attribute_name = re.sub(r'^_{1,2}([^_]*_?)$', r'\g<1>', func.__name__)

            if func.flow_type == 'function':
                func()

            elif func.flow_type == 'attribute':
                try:
                    article_cache[attribute_name] = func()
                except Exception as err:
                    if error_handling == 'raise':
                        raise err
                    elif error_handling == 'catch':
                        article_cache[attribute_name] = err
                    elif error_handling == 'suppress':
                        article_cache[attribute_name] = None
                    else:
                        raise ValueError(f"Invalid value '{error_handling}' for parameter <error_handling>")

            elif func.flow_type == 'filter':
                if func():
                    return None

            else:
                raise ValueError(f'Invalid flow type {func.flow_type} for {func}')

        return article_cache

    def share(self, **kwargs):
        for key, value in kwargs.items():
            self.precomputed.cache[key] = value

    def _wipe(self):
        self.precomputed = Precomputed()

    # base attribute section
    @register_attribute
    def __meta(self) -> Dict[str, Any]:
        return self.precomputed.meta

    @register_attribute
    def __ld(self) -> LinkedData:
        return self.precomputed.ld
