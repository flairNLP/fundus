from datetime import datetime
from textwrap import TextWrapper, dedent
from typing import Any, ClassVar, Dict, List, Optional, Tuple, TypedDict, cast

import langdetect
import lxml.html
from colorama import Fore, Style

from fundus.logging import create_logger
from fundus.parser import ArticleBody, Image
from fundus.scraping.html import HTML
from fundus.utils.serialization import JSONVal, serialize_value

logger = create_logger(__name__)


class Extraction(TypedDict, total=False):
    """Schema for the narrowly-typed subset of extraction keys.

    Parsers may pass additional keys; those live in __extraction__ alongside these
    and are exposed via __getattr__ with type Any. Only the keys declared here are
    type-checked at the property accessors.
    """

    # TODO: once PEP 728 (https://peps.python.org/pep-0728/) is accepted and supported
    #  by our mypy version, inherit from typing_extensions.TypedDict and add the
    #  `extra_items=Any` parameter. That lets us drop the `_narrow` cast workaround and
    #  annotate __init__ kwargs as `**extraction: Unpack[Extraction]` while still
    #  accepting parser-specific extras.

    title: Optional[str]
    body: Optional[ArticleBody]
    authors: List[str]
    publishing_date: Optional[datetime]
    topics: List[str]
    free_access: bool
    images: List[Image]


class Article:
    """A parsed news article: the source HTML plus the parser's extracted attributes.

    Declared attributes (title, body, authors, publishing_date, topics, free_access,
    images) are exposed as type-checked properties; any extra keys a parser returns are
    accessible as read-only attributes via __getattr__. Derived properties (plaintext,
    lang, publisher) are computed on access. Use to_json() to export selected fields.
    """

    DEFAULT_EXPORT_FIELDS: ClassVar[Tuple[str, ...]] = (
        "title",
        "authors",
        "publishing_date",
        "topics",
        "free_access",
        "body",
        "images",
        "plaintext",
        "lang",
        "publisher",
    )

    def __init__(self, *, html: HTML, **extraction: Any) -> None:
        """Build an article from its source HTML and the parser's extracted attributes.

        Args:
            html (HTML): The source document the article was parsed from.
            **extraction (Any): Attributes produced by the parser (e.g. title, body,
                authors). Declared keys are surfaced through typed properties; any
                additional keys are exposed as read-only attributes via __getattr__.

        """
        self.html = html
        self.__extraction__: Dict[str, Any] = extraction

    @property
    def _narrow(self) -> Extraction:
        """View of __extraction__ restricted to the narrowly-typed schema.

        Storage stays Dict[str, Any] because the dict legitimately holds parser-extras
        outside the schema. This cast applies the schema only where it's true: at the
        narrow accessors below.
        """
        return cast(Extraction, self.__extraction__)

    @property
    def title(self) -> Optional[str]:
        return self._narrow.get("title")

    @property
    def body(self) -> Optional[ArticleBody]:
        return self._narrow.get("body")

    @property
    def authors(self) -> List[str]:
        return self._narrow.get("authors", [])

    @property
    def publishing_date(self) -> Optional[datetime]:
        return self._narrow.get("publishing_date")

    @property
    def topics(self) -> List[str]:
        return self._narrow.get("topics", [])

    @property
    def free_access(self) -> bool:
        return self._narrow.get("free_access", False)

    @property
    def images(self) -> List[Image]:
        return self._narrow.get("images", [])

    @property
    def publisher(self) -> str:
        return self.html.source_info.publisher

    def __getattr__(self, item: str) -> Any:
        """Expose parser-extra extraction keys as read-only attributes; raise AttributeError otherwise.

        Only invoked when normal attribute lookup fails.
        """
        # Read from __dict__ directly to avoid infinite recursion when __extraction__ itself isn't
        # set yet (e.g., during unpickling before __setstate__ restores instance state).
        extraction = self.__dict__.get("__extraction__")
        if extraction is None or item not in extraction:
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {item!r}")
        return extraction[item]

    def __setattr__(self, key: str, value: object) -> None:
        """Block writes to extraction-backed attributes; allow all others."""
        # During __init__, html/__extraction__ are assigned before __extraction__ exists;
        # check via __dict__ to avoid triggering __getattr__.
        extraction = self.__dict__.get("__extraction__")
        if extraction is not None and key in extraction:
            raise AttributeError(f"attribute {key!r} is read only")
        object.__setattr__(self, key, value)

    @property
    def plaintext(self) -> Optional[str]:
        body = self.body
        if body is None or isinstance(body, Exception):
            return None
        return str(body) or None

    @property
    def lang(self) -> Optional[str]:
        language: Optional[str] = None

        if self.plaintext:
            try:
                language = langdetect.detect(self.plaintext)
            except langdetect.LangDetectException:
                logger.debug(f"Unable to detect language for article {self.html.responded_url!r}")

        # use @lang attribute of <html> tag as fallback
        if (not language or language == langdetect.detector_factory.Detector.UNKNOWN_LANG) and self.html.content:
            language = lxml.html.fromstring(self.html.content).get("lang")
            if language and "-" in language:
                language = language.split("-")[0]

        return language

    def to_json(self, *fields: str) -> Dict[str, JSONVal]:
        """Export selected article fields as a JSON-compatible dict.

        Args:
            *fields: Field names to export. Each must resolve to an attribute of this
                article (a built-in property or an extraction key). If empty,
                DEFAULT_EXPORT_FIELDS is used. Pass "html" to include the source
                document with its provenance metadata.

        Returns:
            A JSON-serializable dict. Key order matches the order of <fields>.

        Raises:
            KeyError: If a requested field is not present on this article.
            TypeError: If a value's type has no defined serialization.
        """
        selected = fields or self.DEFAULT_EXPORT_FIELDS
        output: Dict[str, JSONVal] = {}
        for field in selected:
            if not hasattr(self, field):
                raise KeyError(field)
            output[field] = serialize_value(getattr(self, field), field)
        return output

    def __str__(self):
        """Render a compact, human-readable summary (title, truncated text, URL, publisher, date)."""
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
            f"{' (' + self.publishing_date.strftime('%Y-%m-%d %H:%M') + ')' if self.publishing_date else ''}"
        )

        return dedent(text)
