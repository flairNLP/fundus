from dataclasses import dataclass, field, fields
from datetime import datetime
from textwrap import TextWrapper, dedent
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import langdetect
import lxml.html
import more_itertools
from colorama import Fore, Style

from fundus.logging import create_logger
from fundus.parser import ArticleBody
from fundus.scraping.html import HTML

logger = create_logger(__name__)


@dataclass(frozen=True)
class Article:
    html: HTML
    exception: Optional[Exception] = None

    # supported (validated) attributes as defined in the guidelines
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    body: Optional[ArticleBody] = None
    publishing_date: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)
    free_access: bool = True

    @classmethod
    def from_extracted(cls, html: HTML, extracted: Dict[str, Any], exception: Optional[Exception] = None) -> "Article":
        validated_attributes: Set[str] = {article_field.name for article_field in fields(cls)}

        extracted_unvalidated: Iterator[Tuple[str, Any]]
        extracted_validated: Iterator[Tuple[str, Any]]
        extracted_unvalidated, extracted_validated = more_itertools.partition(
            lambda attribute_and_value: attribute_and_value[0] in validated_attributes, extracted.items()
        )

        article: Article = cls(html, exception, **dict(extracted_validated))
        for attribute, value in extracted_unvalidated:
            object.__setattr__(article, attribute, value)  # Sets attributes on a frozen dataclass

        return article

    @property
    def plaintext(self) -> Optional[str]:
        return str(self.body) if self.body else None

    @property
    def lang(self) -> Optional[str]:
        language: Optional[str] = None

        if self.plaintext:
            try:
                language = langdetect.detect(self.plaintext)
            except langdetect.LangDetectException:
                logger.debug(f"Unable to detect language for article {self.html.responded_url!r}")

        # use @lang attribute of <html> tag as fallback
        if not language or language == langdetect.detector_factory.Detector.UNKNOWN_LANG:
            language = lxml.html.fromstring(self.html.content).get("lang")
            if language and "-" in language:
                language = language.split("-")[0]

        return language

    def __getattr__(self, item: object) -> Any:
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {str(item)!r}")

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
            f"\n- URL:    {self.html.requested_url}"
            f"\n- From:   {self.html.source_info.publisher}"
            f'{" (" + self.publishing_date.strftime("%Y-%m-%d %H:%M") + ")" if self.publishing_date else ""}'
        )

        return dedent(text)
