from datetime import datetime
from textwrap import TextWrapper, dedent
from typing import Any, Dict, List, Mapping, Optional

import langdetect
import lxml.html
from colorama import Fore, Style

from fundus.logging import create_logger
from fundus.parser import ArticleBody, Image
from fundus.scraping.html import HTML
from fundus.utils.serialization import JSONVal, is_jsonable

logger = create_logger(__name__)


class AttributeView:
    def __init__(self, key: str, extraction: Mapping[str, Any]):
        self.ref = extraction
        self.key = key

    def __get__(self, instance: object, owner: type):
        return self.ref[self.key]

    def __set__(self, obj, value):
        # For now, this is read-only
        raise AttributeError("attribute is read only")


class Article:
    __extraction__: Mapping[str, Any] = {}

    def __init__(self, *, html: HTML, exception: Optional[Exception] = None, **extraction: Any) -> None:
        self.html = html
        self.exception = exception
        self.__extraction__ = extraction

        # create descriptors for attributes that aren't pre-defined as properties.
        for attribute in extraction.keys():
            if not hasattr(self, attribute):
                setattr(self, attribute, AttributeView(attribute, self.__extraction__))

    @property
    def title(self) -> Optional[str]:
        return self.__extraction__.get("title")

    @property
    def body(self) -> Optional[ArticleBody]:
        return self.__extraction__.get("body")

    @property
    def authors(self) -> List[str]:
        return self.__extraction__.get("authors", [])

    @property
    def publishing_date(self) -> Optional[datetime]:
        return self.__extraction__.get("publishing_date")

    @property
    def topics(self) -> List[str]:
        return self.__extraction__.get("topics", [])

    @property
    def free_access(self) -> bool:
        return self.__extraction__.get("free_access", False)

    @property
    def images(self) -> List[Image]:
        return self.__extraction__.get("images", [])

    @property
    def publisher(self) -> str:
        return self.html.source_info.publisher

    def __getattribute__(self, item: str):
        if (attribute := object.__getattribute__(self, item)) and hasattr(attribute, "__get__"):
            return attribute.__get__(self, type(self))
        return attribute

    def __setattr__(self, key: str, value: object):
        if hasattr(self, key):
            # we can't use getattr here, because it would invoke __get__, so unfortunately no default value
            attribute = object.__getattribute__(self, key)
            if hasattr(attribute, "__set__"):
                attribute.__set__(key, value)
                return
        object.__setattr__(self, key, value)

    def __getattr__(self, item: str):
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {str(item)!r}")

    @property
    def plaintext(self) -> Optional[str]:
        return str(self.body) or None if not isinstance(self.body, Exception) else None

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

    def to_json(self, *attributes: str) -> Dict[str, JSONVal]:
        """Converts article object into a JSON serializable dictionary.

        One can specify which attributes should be included by passing attribute names as parameters.
        Default: title, plaintext, authors, publishing_date, topics, free_access + unvalidated attributes

        Args:
            *attributes: The attributes to serialize. Default: see docstring.

        Returns:
            A json serializable dictionary
        """

        # default value for attributes
        if not attributes:
            attributes = tuple(set(self.__extraction__.keys()) - {"meta", "ld"})

        def serialize(v: Any) -> JSONVal:
            if hasattr(v, "serialize"):
                return v.serialize()  # type: ignore[no-any-return]
            elif isinstance(v, datetime):
                return str(v)
            elif not is_jsonable(v):
                raise TypeError(f"Attribute {attribute!r} of type {type(v)!r} is not JSON serializable")
            return v  # type: ignore[no-any-return]

        serialization: Dict[str, JSONVal] = {}
        for attribute in attributes:
            if not hasattr(self, attribute):
                continue
            value = getattr(self, attribute)

            if isinstance(value, list):
                serialization[attribute] = [serialize(item) for item in value]
            else:
                serialization[attribute] = serialize(value)

        return serialization

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

        image_text = (
            f" including {len(self.images)} image(s)" if self.images and not isinstance(self.images, Exception) else ""
        )

        text = (
            f"Fundus-Article{image_text}:"
            f'\n- Title: "{wrapped_title}"'
            f'\n- Text:  "{wrapped_plaintext}"'
            f"\n- URL:    {self.html.requested_url}"
            f"\n- From:   {self.publisher}"
            f'{" (" + self.publishing_date.strftime("%Y-%m-%d %H:%M") + ")" if self.publishing_date else ""}'
        )

        return dedent(text)
