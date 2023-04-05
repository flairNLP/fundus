from dataclasses import dataclass, field
from datetime import datetime
from textwrap import TextWrapper, dedent
from typing import Any, Dict, List, Optional

import more_itertools
from colorama import Fore, Style

from src.parser.html_parser import ArticleBody


@dataclass(frozen=True)
class ArticleSource:
    url: str
    html: str
    crawl_date: datetime
    publisher: Optional[str] = None
    crawler_ref: object = None


@dataclass(frozen=True)
class Article:
    source: ArticleSource
    exception: Optional[Exception] = None

    # supported attributes as defined in the guidelines
    title: Optional[str] = None
    author: List[str] = field(default_factory=list)
    body: Optional[ArticleBody] = None
    publishing_date: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)

    @classmethod
    def from_extracted(cls, source: ArticleSource, extracted: Dict[str, Any], exception: Optional[Exception] = None):
        unsupported, supported = more_itertools.partition(
            lambda view: view[0] in cls.__annotations__, extracted.items()
        )

        new = cls(source, exception, **dict(supported))
        for attr, value in unsupported:
            object.__setattr__(new, attr, value)

        return new

    @property
    def plaintext(self) -> Optional[str]:
        body = self.body
        return str(body) if body else None

    def __getattr__(self, item):
        raise AttributeError(f"Article has no attribute '{item}'")

    def __str__(self):
        # the subsequent indent here is a bit wacky, but textwrapper.dedent won't work with tabs, so we have to use
        # whitespaces instead.
        title_wrapper = TextWrapper(width=80, max_lines=1, initial_indent="")
        text_wrapper = TextWrapper(width=80, max_lines=2, initial_indent="", subsequent_indent="          ")
        wrapped_title = title_wrapper.fill(
            f"{Fore.RED}--missing title--{Style.RESET_ALL}" if self.title is None else self.title.strip()
        )
        wrapped_plaintext = text_wrapper.fill(
            f"{Fore.RED}--missing plaintext--{Style.RESET_ALL}" if self.plaintext is None else self.plaintext.strip()
        )

        text = (
            f"Fundus-Article:"
            f'\n- Title: "{wrapped_title}"'
            f'\n- Text:  "{wrapped_plaintext}"'
            f"\n- URL:    {self.source.url}"
            f'\n- From:   {self.source.publisher} ({self.publishing_date.strftime("%Y-%m-%d %H:%M") if self.publishing_date else ""})'
        )

        return dedent(text)
