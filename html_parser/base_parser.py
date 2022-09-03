import functools
import re
from functools import partial
from typing import List, Callable, Dict, Optional, Any, Literal, Union

import lxml.html


class RegisteredFunction:
    __wrapped__ = None

    def __init__(self,
                 func: Union[Callable, partial],
                 flow_type: str,
                 priority: Optional[int] = None):

        self.func = func
        self.flow_type = flow_type
        self.priority = priority

    def __call__(self, *args, **kwargs):
        return self.func(*args, *kwargs)

    def __lt__(self, other):
        if self.priority is None:
            return False
        elif other.priority is None:
            return True
        else:
            return self.priority < other.priority

    def __repr__(self):
        return f"registered {self.flow_type}: {self.__wrapped__} --> '{self.__name__}'"


class BaseParser:

    def __init__(self):
        self._shared_object_buffer: Dict[str, Any] = {}
        self._func_flow: List[RegisteredFunction] = []

        registered_functions: List[RegisteredFunction] = []
        for func_name in dir(self):
            registered_function = getattr(self, func_name)
            if isinstance(registered_function, RegisteredFunction):
                registered_function.func = partial(registered_function.func, self)
                registered_functions.append(registered_function)

        self._func_flow = sorted(registered_functions)

    class Utility:

        @staticmethod
        def get_meta_content(tree: lxml.html.HtmlElement) -> Dict[str, str]:
            meta_node_selector = 'head > meta[name], head > meta[property]'
            meta_nodes = tree.cssselect(meta_node_selector)
            return {node.attrib.get('name') or node.attrib.get('property'): node.attrib.get('content')
                    for node in meta_nodes}

        @staticmethod
        def strip_nodes_to_text(text_nodes: List) -> Optional[str]:
            if not text_nodes:
                return None
            return "\n\n".join(([re.sub(r'\n+', ' ', node.text_content()) for node in text_nodes])).strip()

    @property
    def cache(self) -> Dict[str, Any]:
        return self._shared_object_buffer

    @property
    def attributes(self) -> List[str]:
        if self._func_flow:
            return [func.__name__ for func in self._func_flow if func.flow_type == 'attribute']

    @staticmethod
    def _register(cls=None, *, flow_type: Literal['attribute', 'function', 'filter'], priority=None):

        def wrapper(func):
            return functools.update_wrapper(RegisteredFunction(func, flow_type, priority), func)

        if cls is None:
            return wrapper

        return wrapper(cls)

    @staticmethod
    def register_attribute(cls=None, priority: int = None):
        return BaseParser._register(cls, flow_type='attribute', priority=priority)

    @staticmethod
    def register_control(cls=None, priority: int = None):
        return BaseParser._register(cls, flow_type='function', priority=priority)

    @staticmethod
    def register_filter(cls=None, priority: int = None):
        return BaseParser._register(cls, flow_type='filter', priority=priority)

    def parse(self, html: str, **kwargs) -> Optional[Dict[str, Any]]:

        # wipe existing shared cache
        self._wipe()

        # share html and kwargs among cache
        self.share(html=html, **kwargs)

        article_cache = {}

        for func in self._func_flow:
            # TODO: replace with match statement once we have python 3.9
            if func.flow_type == 'function':
                func()
            elif func.flow_type == 'attribute':
                article_cache[func.__name__] = func()
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
