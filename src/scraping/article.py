import json
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from textwrap import TextWrapper, dedent
from typing import Any, Callable, List, Dict, Optional

from colorama import Fore, Style

from src.parser.html_parser import ArticleBody, LinkedData


@dataclass(frozen=True)
class BaseArticle(ABC):
    url: str
    html: str
    crawl_date: datetime

    def serialize(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]):
        return cls(**serialized)

    def pprint(self, indent: int = 4, ensure_ascii: bool = False, default: Callable[[Any], Any] = str,
               exclude: List[str] = None) -> str:
        to_serialize: Dict[str, Any] = self.__dict__.copy()
        for key in exclude:
            if not hasattr(self, key):
                raise AttributeError(f"Tried to exclude key '{key} which isn't present in this'{self}' instance")
            to_serialize.pop(key)
        return json.dumps(to_serialize, indent=indent, ensure_ascii=ensure_ascii, default=default)


@dataclass(frozen=True)
class ArticleSource(BaseArticle):
    source: object


@dataclass(frozen=True)
class Article(BaseArticle):
    extracted: Dict[str, Any]
    exception: Exception = None
    source: str = None

    @property
    def complete(self) -> bool:
        return all(not (isinstance(attr, Exception) or attr is None) for attr in self.extracted.values())

    # provide direct access for commonly used attributes in self.extracted
    @property
    def plaintext(self) -> Optional[str]:
        body = self.body
        return str(body) if body else None

    @property
    def title(self) -> Optional[str]:
        return self.extracted.get('title') if self.extracted else None

    @property
    def body(self) -> Optional[ArticleBody]:
        return self.extracted.get('body') if self.extracted else None

    @property
    def authors(self) -> List[str]:
        return self.extracted.get('authors', []) if self.extracted else None

    @property
    def ld(self) -> Optional[LinkedData]:
        return self.extracted.get('ld') if self.extracted else None

    @property
    def meta(self):
        return self.extracted.get('meta') if self.extracted else None

    def __str__(self):
        # the subsequent indent here is a bit wacky, but textwrapper.dedent won't work with tabs, so we have to use
        # whitespaces instead.
        text_wrapper = TextWrapper(width=100, max_lines=5, initial_indent='"', subsequent_indent='             ')
        wrapped_title = text_wrapper.fill(self.title or f"{Fore.RED}--missing title--{Style.RESET_ALL}")
        wrapped_plaintext = text_wrapper.fill(self.plaintext or f"{Fore.RED}--missing plaintext--{Style.RESET_ALL}")

        text = f"""
            {wrapped_title}"
                - by {', '.join(self.authors) if self.authors else f"{Fore.RED}--missing authors--{Style.RESET_ALL}"}
            
            {wrapped_plaintext}"
            
            from: {self.url}
        """

        return dedent(text)
