import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, ClassVar, Dict, Iterator, List, Mapping, Optional, Pattern, Tuple
from urllib.parse import quote, urlencode, urlsplit

import dateparser
import lxml.html
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, Timeout
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    image_extraction,
    normalize_whitespace,
)
from fundus.scraping.session import InterruptableSession
from fundus.scraping.url import URLSource

logger = create_logger(__name__)

__all__ = ["EDITIONS", "Edition", "WikinewsAPI", "WikinewsParser"]

# Cheap guard so that obvious non-dates never reach the parser. Lookarounds rather than
# \b, so a year butting against a non-Latin script still matches ('2026年2月26日').
_YEAR_PATTERN: Pattern[str] = re.compile(r"(?<!\d)\d{4}(?!\d)")

# Year-first spellings are the only ones an edition-agnostic reading may rely on: they are
# unambiguous whatever the locale. Anything written day-first or in words needs the
# edition's ``date_language``, or a normalizer that rewrites it into this form.
_YEAR_FIRST_PATTERNS: Tuple[Pattern[str], ...] = (
    re.compile(r"^(?P<year>\d{4})[-/.](?P<month>\d{1,2})[-/.](?P<day>\d{1,2})$"),
)


def _reject_future(date: Optional[datetime]) -> Optional[datetime]:
    """Discard dates that cannot be publication dates.

    A handful of Wikinews pages date themselves through a template that renders the
    *current* date rather than the stored one, which yields an article published in the
    future. No date at all beats a confidently wrong one.
    """
    if date is not None and date.date() > datetime.now().date():
        return None
    return date


# --- how each edition spells a date -------------------------------------------------

#: Bulgarian files under a sentence rather than a date: 'Новини от 26 ноември 2016 г.' --
#: 'News from ...' with the year abbreviation trailing. Only what sits between is a date.
_BULGARIAN_WRAPPER: Pattern[str] = re.compile(r"^Новини\s+от\s+|\s*г\.\s*$")

#: Esperanto declines the day as an ordinal -- '4-a de majo 2026', 'the 4th of May'.
#: dateparser knows the month names but reads the cardinal form only.
_ESPERANTO_ORDINAL_DAY: Pattern[str] = re.compile(r"(?<!\d)(\d{1,2})-a\s+de\s+")

#: Limburgish labels the category before dating it: 'Datum: oktober 2, 2011'.
_LIMBURGISH_LABEL: Pattern[str] = re.compile(r"^Datum:\s*")

#: Thai dates the Buddhist era: '16 มีนาคม พ.ศ. 2554' is 2011-03-16. dateparser reads the
#: month names but not the era marker, and a BE year handed over verbatim lands five
#: centuries out, where _reject_future discards it.
_BUDDHIST_ERA: Pattern[str] = re.compile(r"พ\.?\s*ศ\.?\s*(?P<year>\d{4})")
_BUDDHIST_ERA_OFFSET = 543

#: Gun and Sindhi have no dateparser locale, so their month names are mapped by hand and
#: the category rewritten year-first, which _YEAR_FIRST_PATTERNS then reads.
#:
#: Gun writes two orthographies side by side, Gun (Bénin) and Gungbe, and runs many
#: stories in both; every pair below was confirmed by matching those duplicate articles
#: against each other, so both spellings are listed.
_GUN_MONTHS: Mapping[str, int] = {
    "Alunlunsun": 1,
    "Afínplọsun": 2,
    "Afínkplɔsun": 2,
    "Whejisun": 3,
    "Xwejisun": 3,
    "Lidosun": 4,
    "Liɖosun": 4,
    "Nuwhàsun": 5,
    "Nuxwàsun": 5,
    "Ayidosun": 6,
    "Liyasun": 7,
    "Avivọsun": 8,
    "Avivɔsun": 8,
    "Zósun": 9,
    "Kọ́yànsun": 10,
    "Kɔ́nyàsun": 10,
    "Abọ̀húsun": 11,
    "Abɔ̀xúsun": 11,
    "Awewesun": 12,
}
#: Four names is the whole Sindhi calendar: the edition published from October 2006 to
#: January 2007 and nothing since. The day counts corroborate the reading -- 30 for
#: November, 31 for December and January, 14 for October, where the wiki started mid-month.
_SINDHI_MONTHS: Mapping[str, int] = {
    "جنوري": 1,
    "آڪٽوبر": 10,
    "نومبر": 11,
    "ڊسمبر": 12,
}
_GUN_DATE: Pattern[str] = re.compile(r"^(?P<month>\S+)\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4})$")
_SINDHI_DATE: Pattern[str] = re.compile(r"^(?P<day>\d{1,2})\s+(?P<month>\S+)\s+(?P<year>\d{4})$")

#: CJK numeric spellings, which dateparser has no reading for.
_CJK_NUMERIC_DATE: Tuple[Pattern[str], ...] = (
    re.compile(r"^(?P<year>\d{4})\s*年\s*(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日$"),
)
_KOREAN_NUMERIC_DATE: Tuple[Pattern[str], ...] = (
    re.compile(r"^(?P<year>\d{4})\s*년\s*(?P<month>\d{1,2})\s*월\s*(?P<day>\d{1,2})\s*일$"),
)

#: A character of Chinese, Japanese or Korean carries several times the text of a Latin
#: one, so the shared 60-character prose floor reads whole sentences as navigation: in a
#: typical ja article 8 of 11 sentences run shorter than that and carry a wikilink.
_CJK_PROSE_LENGTH = 20


def _strip(pattern: Pattern[str]) -> Callable[[str], str]:
    """Normalizer removing everything <pattern> matches."""

    def normalize(text: str) -> str:
        return pattern.sub("", text)

    return normalize


def _cardinalize_esperanto_day(text: str) -> str:
    return _ESPERANTO_ORDINAL_DAY.sub(r"\1 ", text)


def _gregorian_from_buddhist(text: str) -> str:
    return _BUDDHIST_ERA.sub(lambda match: str(int(match.group("year")) - _BUDDHIST_ERA_OFFSET), text)


def _months_to_year_first(months: Mapping[str, int], pattern: Pattern[str]) -> Callable[[str], str]:
    """Normalizer rewriting '<month name> <day>, <year>' into the year-first form.

    The output is deliberately unpadded -- ``_YEAR_FIRST_PATTERNS`` accepts ``\\d{1,2}``
    and padding would only add a way to get it wrong.
    """

    def normalize(text: str) -> str:
        if (match := pattern.match(text)) and (month := months.get(match.group("month"))):
            return f"{match.group('year')}-{month}-{match.group('day')}"
        return text

    return normalize


# --- the editions -------------------------------------------------------------------


@dataclass(frozen=True)
class Edition:
    """What one Wikinews edition does differently.

    Every field defaults to the shared behaviour, so an edition that writes year-first
    dates and nothing unusual is a bare ``Edition()``; naming a ``date_language`` is
    enough for most of the rest.
    """

    #: Language the edition writes its dates in, as dateparser spells it. Left unset when
    #: dateparser has no locale for it, in which case only year-first dates are read --
    #: possibly after ``normalize_date`` has rewritten them into that form.
    date_language: Optional[str] = None
    #: Spellings dateparser has no reading for, tried before it.
    date_patterns: Tuple[Pattern[str], ...] = ()
    #: Rewrites a category into something readable: strips a template's wording, declines
    #: an ordinal, converts an era, maps month names.
    normalize_date: Optional[Callable[[str], str]] = None
    date_order: str = "DMY"
    #: Characters below which a block of pure links reads as chrome rather than prose.
    prose_length: int = 60
    #: Whether body lists may be taken from below the first h2. Off everywhere but ``en``,
    #: whose interviews run the whole Q&A down there.
    lists_anywhere: bool = False


#: Active language editions per Special:SiteMatrix, and what each does differently.
#: Codes are ISO 639-1 except for Gun ('guw') and Shan ('shn'), which have no two-letter
#: form and are therefore referenced by their ISO 639-3 code.
EDITIONS: Mapping[str, Edition] = {
    "ar": Edition("ar"),
    "bg": Edition("bg", normalize_date=_strip(_BULGARIAN_WRAPPER)),
    "bs": Edition("bs"),
    "ca": Edition("ca"),
    "cs": Edition("cs"),
    "de": Edition("de"),
    "el": Edition("el"),
    "en": Edition("en", lists_anywhere=True),
    "eo": Edition("eo", normalize_date=_cardinalize_esperanto_day),
    "es": Edition("es"),
    "fa": Edition("fa"),
    "fi": Edition("fi"),
    "fr": Edition("fr"),
    "guw": Edition(normalize_date=_months_to_year_first(_GUN_MONTHS, _GUN_DATE)),
    "he": Edition("he"),
    "hu": Edition("hu"),
    "it": Edition("it"),
    "ja": Edition("ja", date_patterns=_CJK_NUMERIC_DATE, prose_length=_CJK_PROSE_LENGTH),
    "ko": Edition("ko", date_patterns=_KOREAN_NUMERIC_DATE, prose_length=_CJK_PROSE_LENGTH),
    # Limburgish has no locale of its own but names its months in Dutch.
    "li": Edition("nl", normalize_date=_strip(_LIMBURGISH_LABEL)),
    "nl": Edition("nl"),
    # dateparser has no 'no' locale; Bokmål reads the edition's dates.
    "no": Edition("nb"),
    "pl": Edition("pl"),
    "pt": Edition("pt"),
    "ro": Edition("ro"),
    "ru": Edition("ru"),
    "sd": Edition(normalize_date=_months_to_year_first(_SINDHI_MONTHS, _SINDHI_DATE)),
    "shn": Edition(),
    "sq": Edition("sq"),
    "sr": Edition("sr"),
    "sv": Edition("sv"),
    "ta": Edition("ta"),
    "th": Edition("th", normalize_date=_gregorian_from_buddhist),
    "tr": Edition("tr"),
    "uk": Edition("uk"),
    "zh": Edition("zh", date_patterns=_CJK_NUMERIC_DATE, prose_length=_CJK_PROSE_LENGTH),
}

#: Used for a page whose edition cannot be identified. Reads year-first dates and nothing
#: else, which is the most any edition-agnostic reading can claim.
DEFAULT_EDITION = Edition()

_HOST_SUFFIX = ".wikinews.org"


@dataclass
class WikinewsAPI(URLSource):
    """Yields every mainspace article of one Wikinews edition, in title order.

    Wikinews publishes no crawlable sitemap, so articles are enumerated through
    the MediaWiki API instead. ``list=allpages`` is the only module that walks a
    whole wiki, and it walks it by title: the ``page`` table is indexed on
    ``(page_namespace, page_title)`` and holds no creation timestamp at all, so
    publication order is not on offer from the API. Ordering client-side means
    buffering every title before the first URL can be yielded -- 1.5 million of
    them on the Russian edition -- so each batch is yielded as it arrives instead.

    Order is therefore arbitrary with respect to publication date. Capping a crawl
    with ``max_articles`` returns the alphabetically first articles rather than the
    newest ones, and the same ones on every run.

    Articles are linked by their canonical ``/wiki/`` URL rather than one of the
    REST HTML endpoints, because robots.txt disallows both ``/w/`` and ``/api/``
    for every user agent.
    """

    # Override these two in a subclass to point at another WMF project.
    _api_url: ClassVar[str] = "https://{language}.wikinews.org/w/api.php"
    _article_url: ClassVar[str] = "https://{language}.wikinews.org/wiki/{title}"

    _batch_size: ClassVar[int] = 500  # API cap for anonymous clients
    _max_lag: ClassVar[int] = 5  # seconds of replica lag we tolerate
    _max_retries: ClassVar[int] = 3
    _backoff: ClassVar[float] = 2.0

    def __init__(self, language: str) -> None:
        """
        Args:
            language: Wikinews language code, e.g. ``"de"``. Each edition lives on
                its own subdomain and carries exactly that one language, so it
                determines the API host, the article host and ``languages``.
        """
        super().__init__(url=self._api_url.format(language=language), languages={language}, interleave=True)
        self.language = language

    def article_url(self, title: str) -> str:
        """Return the canonical article URL for a MediaWiki title."""
        # ':' and '/' stay literal to match the canonical form MediaWiki itself
        # advertises via <link rel="canonical">.
        return self._article_url.format(language=self.language, title=quote(title.replace(" ", "_"), safe=":/"))

    def _query(
        self, session: InterruptableSession, headers: Dict[str, str], params: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Run one API call, retrying while the replicas are lagged."""
        for attempt in range(self._max_retries):
            try:
                response = session.get_with_interrupt(url=f"{self.url}?{urlencode(params)}", headers=headers)

            except (HTTPError, ConnectionError, Timeout) as error:
                logger.warning(f"Warning! Couldn't reach the {self.language} Wikinews API because of {error!r}")
                return None
            except Exception as error:
                logger.error(
                    f"Warning! Couldn't query the {self.language} Wikinews API because of an unexpected error {error!r}"
                )
                return None

            try:
                payload: Dict[str, Any] = response.json()
            except ValueError as error:
                logger.warning(f"Warning! The {self.language} Wikinews API returned malformed JSON: {error!r}")
                return None

            if (failure := payload.get("error")) is None:
                return payload
            if failure.get("code") != "maxlag":
                logger.warning(f"Warning! The {self.language} Wikinews API rejected the query: {failure.get('info')}")
                return None
            time.sleep(self._backoff * (attempt + 1))

        logger.warning(f"Warning! The {self.language} Wikinews API stayed lagged over {self._max_retries} attempts")
        return None

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        # Creation dates would be the natural sort key, but there is no way to read them
        # for more than one page at a time: pairing a generator with
        # prop=revisions&rvdir=newer&rvlimit=1 is rejected as 'invalidparammix', because
        # the revision index is keyed on the page, so that lookup is one seek per page.
        params: Dict[str, str] = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "list": "allpages",
            "apnamespace": "0",
            "apfilterredir": "nonredirects",
            "aplimit": str(self._batch_size),
            "maxlag": str(self._max_lag),
            # Every edition's front page is a mainspace non-redirect just like an article,
            # so allpages hands it over. It is asked for alongside the first batch rather
            # than in a request of its own, meta modules composing with list modules.
            "meta": "siteinfo",
            "siprop": "general",
        }

        main_page: Optional[str] = None
        empty = True
        while True:
            if (payload := self._query(session, headers, params)) is None:
                # Whatever was yielded so far stands, as it does for a failed sitemap.
                return
            if "meta" in params:
                main_page = payload.get("query", {}).get("general", {}).get("mainpage")
                # siteinfo does not paginate, so carrying it along would only refetch it.
                del params["meta"], params["siprop"]
            for page in payload.get("query", {}).get("allpages", []):
                if page["title"] == main_page:
                    continue  # a portal of headline links, not an article
                empty = False
                yield self.article_url(page["title"])
            # A batch can come back empty with articles still to come: the wikis run in
            # miser mode, where <aplimit> caps the rows scanned rather than the rows
            # returned, and apfilterredir is applied afterwards. Only <continue> going
            # missing means the edition is exhausted.
            if not (continuation := payload.get("continue")):
                break
            params.update(continuation)

        if empty:
            logger.warning(f"Warning! The {self.language} Wikinews API returned no articles")


#: The article and all its templated furniture sit side by side in here.
_CONTENT = "//div[contains(@class, 'mw-parser-output')]"
# Templated furniture is identified by class rather than by heading text, which would
# differ per language. Matched on any ancestor, not just div: 'related news' boxes are
# tables, and reference and licence blocks carry their own classes.
_CHROME = (
    "not(ancestor-or-self::*[contains(@class, 'infobox') or contains(@class, 'noprint')"
    " or contains(@class, 'nomobile') or contains(@class, 'mf-mobile-only')"
    " or contains(@class, 'plainlinks') or contains(@class, 'current')"
    " or contains(@class, 'metadata') or contains(@class, 'gallery')"
    " or contains(@class, 'toccolours') or contains(@class, 'references')"
    " or contains(@class, 'boilerplate')])"
)
# Prose is taken from the whole page. Interviews and newsletters structure their text with
# headings and so carry article content well below the first one, while the trailing
# boilerplate sections (Sources, Related articles, Sister links) hold only link lists.
# Bulleted lists are therefore the exception and stay above the first h2, which is
# precisely where those link lists begin.
_ABOVE = "not(preceding::div[contains(@class, 'mw-heading2')])"


def _prose_filter(min_length: int) -> str:
    """Predicate keeping a block unless it is a short run of pure links.

    Templated footers -- 'Kommentar abgeben', navigation strips -- are short runs of links
    carrying no class to filter on, so length is what separates them from prose. The count
    is in characters, which makes it script-relative; see ``_CJK_PROSE_LENGTH``.
    """
    return f"[not(.//a) or string-length(normalize-space(.)) >= {min_length}]"


def _paragraph_xpath(content: str, chrome: str, prose: str, above: str) -> str:
    """Compose the body selector out of the four block kinds MediaWiki renders prose as.

    ``<p>`` is the ordinary case. The other three are how wikitext spells a list, and each
    needs its own guard:

    * ``<ul>`` (``*``) is what the trailing boilerplate sections are built from -- Sources,
      Related articles, Sister links -- so it is confined to above the first h2.
    * ``<ol>`` (``#``) is not used for those, so it is taken anywhere; ``prose`` keeps out
      the sister-project boxes, which are link-only.
    * ``<dl>`` (``;``/``:``) carries indented prose and result lists. Only the innermost
      ``dd`` is taken, or a nested list would contribute its text once per level.
    """
    return (
        f"{content}//p[normalize-space()][{chrome}]{prose}"
        f" | {content}//ul[{above}][{chrome}][not(contains(@class, 'gallery'))]/li"
        f" | {content}//ol[{chrome}][not(contains(@class, 'gallery'))]/li{prose}"
        f" | {content}//dl[{above}][{chrome}]/dd[not(.//dl)]"
    )


#: One compiled selector per body shape any edition asks for. Built over the whole table
#: plus the default, so the lookup in ``_paragraph_selector`` is total: a KeyError there
#: would escape ``BaseParser.__init__``, which walks the instance's members and swallows
#: only AttributeError.
_PARAGRAPH_SELECTORS: Dict[Tuple[int, bool], XPath] = {
    (prose_length, lists_anywhere): XPath(
        _paragraph_xpath(
            _CONTENT,
            _CHROME,
            _prose_filter(prose_length),
            "true()" if lists_anywhere else _ABOVE,
        )
    )
    for prose_length, lists_anywhere in {
        (edition.prose_length, edition.lists_anywhere) for edition in (*EDITIONS.values(), DEFAULT_EDITION)
    }
}


class WikinewsParser(ParserProxy):
    """What every Wikinews edition has in common: MediaWiki's rendering.

    A rendered page is flat -- the article, its headings and all the templated furniture
    (publication banner, share box, comment prompt) sit side by side as children of
    ``div.mw-parser-output``. Everything structural here keys off that rather than off
    text, so it holds for an edition in any language: chrome is recognised by class, the
    article's end by the first h2, its date by the category Wikinews files it under.

    What the editions do *not* share is how they spell that date, and how much text a
    character of their script carries. Those live in :data:`EDITIONS`, selected per
    document, because one publisher covers every edition and a parser is handed only the
    HTML -- never the publisher it came from.
    """

    class V1(BaseParser):
        _subheadline_selector = XPath(f"{_CONTENT}//div[contains(@class, 'mw-heading3')][{_CHROME}]/h3")
        _content_selector = XPath(_CONTENT)
        _image_selector = XPath(f"{_CONTENT}//figure[{_ABOVE}][{_CHROME}]//img")
        # MediaWiki serves protocol-relative image URLs, so image_extraction needs an
        # absolute base to resolve them against.
        _canonical_selector = XPath("string(//link[@rel='canonical']/@href)")
        _title_selector = XPath("//h1[@id='firstHeading']")
        # Only the visible categories; MediaWiki keeps maintenance ones, which are no use
        # as topics, in a separate hidden container.
        _category_selector = XPath("//div[@id='mw-normal-catlinks']//li/a")
        # hCalendar microformat emitted by some editions' publication template
        _published_selector = XPath("//*[contains(@class, 'value-title')]/@title")

        def _edition_code(self) -> Optional[str]:
            """The edition this document belongs to, read off the document itself.

            The canonical link is the primary key: MediaWiki emits it on every page and
            its host is the edition's subdomain. ``<html lang>`` is the fallback, correct
            for every edition but ``no``, which reports its Bokmål code 'nb' -- and that
            happens to be exactly the ``date_language`` that edition wants anyway.
            """
            host = urlsplit(self._canonical_selector(self.precomputed.doc)).hostname or ""
            if host.endswith(_HOST_SUFFIX):
                return host[: -len(_HOST_SUFFIX)].rsplit(".", 1)[-1]
            return (self.precomputed.doc.get("lang") or "").split("-")[0] or None

        @property
        def _edition(self) -> Edition:
            # Memoised in the per-parse cache, which _base_setup rebuilds for every
            # document, so nothing carries between articles.
            if (edition := self.precomputed.cache.get("edition")) is None:
                code = self._edition_code()
                if (edition := EDITIONS.get(code or "")) is None:
                    logger.warning(f"Warning! Unrecognised Wikinews edition {code!r}; reading year-first dates only")
                    edition = DEFAULT_EDITION
                self.precomputed.cache["edition"] = edition
            return edition

        @property
        def _paragraph_selector(self) -> XPath:
            edition = self._edition
            return _PARAGRAPH_SELECTORS[(edition.prose_length, edition.lists_anywhere)]

        def _read_date(self, text: str) -> Optional[datetime]:
            """Read a full date out of <text>, or return None if it holds none.

            STRICT_PARSING is what keeps topics out: a category such as
            'Fußball-Weltmeisterschaft 2026' is not a date, and a lenient parser answers
            it with today's.
            """
            text = text.strip()
            if not _YEAR_PATTERN.search(text):
                return None

            edition = self._edition
            # Normalizing before the patterns run lets an edition rewrite its dates into
            # the year-first form and be read without a dateparser locale at all.
            if edition.normalize_date is not None:
                text = edition.normalize_date(text)

            for pattern in (*_YEAR_FIRST_PATTERNS, *edition.date_patterns):
                if match := pattern.match(text):
                    try:
                        return _reject_future(
                            datetime(int(match.group("year")), int(match.group("month")), int(match.group("day")))
                        )
                    except ValueError:
                        return None  # e.g. a 13th month: not a date after all

            if edition.date_language is None:
                return None
            return _reject_future(
                dateparser.parse(
                    text,
                    languages=[edition.date_language],
                    settings={"DATE_ORDER": edition.date_order, "STRICT_PARSING": True},
                )
            )

        def _categories(self, doc: lxml.html.HtmlElement) -> List[str]:
            names = [normalize_whitespace(node.text_content()) for node in self._category_selector(doc)]
            return list(dict.fromkeys(filter(bool, names)))  # de-duplicate, preserving order

        @attribute
        def title(self) -> Optional[str]:
            # <title> carries a localised site suffix ('... - Wikinews, the free news
            # source'), so take the heading instead.
            if heading := self._title_selector(self.precomputed.doc):
                return normalize_whitespace(heading[0].text_content()) or None
            return None

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        # No 'authors' attribute: Wikinews articles are written collaboratively and carry
        # no byline, so attribution lives in the page history rather than the article.

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            if published := self._published_selector(self.precomputed.doc):
                if date := self._read_date(published[0]):
                    return date
            # Every published article is filed under a category named after its
            # publication date, e.g. 'Kategorie:21.04.2025' or 'Category:March 21, 2026'.
            for category in self._categories(self.precomputed.doc):
                if date := self._read_date(category):
                    return date
            return None

        @attribute
        def topics(self) -> List[str]:
            return [category for category in self._categories(self.precomputed.doc) if not self._read_date(category)]

        @attribute
        def images(self) -> List[Image]:
            # image_extraction derives its lower bound from the last paragraph and raises
            # when there is none, which happens on editions this parser cannot read.
            if not self._paragraph_selector(self.precomputed.doc):
                return []
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=self._image_selector,
                upper_boundary_selector=self._content_selector,
                relative_urls=self._canonical_selector,
            )
