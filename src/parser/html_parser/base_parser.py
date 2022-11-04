import functools
import inspect
import json
from abc import ABC
from typing import List, Callable, Dict, Optional, Any, Literal, Union, Set

import lxml.html

from src.parser.html_parser.utility import get_meta_content


class RegisteredFunction:
    __wrapped__: callable = None
    __func__: callable
    __self__: object

    # TODO: ensure uint for priority instead of int
    def __init__(self,
                 func: Callable,
                 flow_type: str,
                 priority: Optional[int] = None):

        self.__func__ = func
        self.flow_type = flow_type
        self.priority = priority

    def __get__(self, instance, owner):
        self.__self__ = instance
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


class BaseParser:

    def __init__(self):
        self._shared_object_buffer: Dict[str, Any] = {}

        registered_functions = [func for _, func in
                                inspect.getmembers(self, predicate=lambda x: isinstance(x, RegisteredFunction))]

        self._func_flow: dict[str, RegisteredFunction] = {func.__name__: func for func in sorted(registered_functions)}

    @property
    def cache(self) -> Dict[str, Any]:
        return self._shared_object_buffer

    @classmethod
    def attributes(cls):
        return [func.__name__ for _, func in
                inspect.getmembers(cls, predicate=lambda x: isinstance(x, RegisteredFunction))]

    def _base_setup(self):
        content = self.cache['html']
        doc = lxml.html.fromstring(content)
        ld_content = doc.xpath('string(//script[@type="application/ld+json"]/text())')
        ld = json.loads(ld_content) or {}
        meta = get_meta_content(doc) or {}
        self.share(doc=doc, ld=ld, meta=meta)

    def parse(self, html: str,
              error_handling: Literal['suppress', 'catch', 'raise'] = 'raise') -> Optional[Dict[str, Any]]:

        # wipe existing shared cache
        self._wipe()

        # share html and kwargs among cache
        self.share(html=html)

        self._base_setup()

        article_cache = {}

        for func in self._func_flow.values():
            # TODO: replace with match statement once we have python 3.10

            if func.flow_type == 'function':
                func()

            elif func.flow_type == 'attribute':
                try:
                    article_cache[func.__name__] = func()
                except Exception as err:
                    match error_handling:
                        case 'raise':
                            raise err
                        case 'catch':
                            article_cache[func.__name__] = err
                        case 'suppress':
                            article_cache[func.__name__] = None
            elif func.flow_type == 'filter':
                if func():
                    return None
            else:
                raise ValueError(f'Invalid function flow type {func.flow_type}')

        return article_cache

    def share(self, **kwargs):
        for key, value in kwargs.items():
            self._shared_object_buffer[key] = value

    def _wipe(self):
        self._shared_object_buffer = {}

    # base attribute section
    @register_attribute
    def meta(self) -> dict[str, Any]:
        return self.cache.get('meta')

    @register_attribute
    def ld(self) -> dict[str, Any]:
        return self.cache.get('ld')
