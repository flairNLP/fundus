import datetime
from typing import Any, Dict, List, Optional

import lxml.html
import pytest
from lxml.etree import XPath

from fundus import Article
from fundus.parser import ArticleBody, LiveTickerBody
from fundus.parser.data import (
    ArticleSection,
    Image,
    ImageVersion,
    LiveTickerEntry,
    TextSequence,
)
from fundus.parser.utility import extract_live_ticker_body_with_selector
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.publication import LiveTicker

info = SourceInfo(publisher="")
html = HTML(content="", responded_url="", requested_url="", crawl_date=datetime.datetime.now(), source_info=info)


def build_image(url: str = "https://example.com/image.jpg") -> Image:
    return Image(
        versions=[ImageVersion(url=url)],
        is_cover=False,
        description=None,
        caption=None,
        authors=[],
        position=0,
    )


def build_entry(
    headline: str = "",
    paragraphs: Optional[List[str]] = None,
    authors: Optional[List[str]] = None,
    images: Optional[List[Image]] = None,
    publishing_date: datetime.datetime = datetime.datetime(2025, 1, 1),
) -> LiveTickerEntry:
    paragraphs = ["Paragraph"] if paragraphs is None else paragraphs
    return LiveTickerEntry(
        sections=[ArticleSection(TextSequence([headline] if headline else []), TextSequence(paragraphs))],
        publishing_date=publishing_date,
        authors=authors or [],
        images=images or [],
        html=f"<div>{' '.join(paragraphs)}</div>",
    )


class TestLiveTicker:
    def test_constructor(self):
        extraction = {"authors": ["Author"], "title": "title"}

        with pytest.raises(TypeError):
            LiveTicker(extraction, html=html)  # type: ignore[arg-type, misc]

        with pytest.raises(TypeError):
            LiveTicker(**extraction)  # type: ignore[arg-type]

        LiveTicker(**{}, html=html)
        LiveTicker(**extraction, html=html, exception=None)
        LiveTicker(html=html, **extraction, exception=None)
        LiveTicker(**extraction, html=html, exception=TypeError())

    def test_default_values(self):
        extraction: Dict[str, Any] = {}

        live_ticker = LiveTicker(**extraction, html=html)

        assert live_ticker.title is None
        assert live_ticker.body is None
        assert live_ticker.authors == []
        assert live_ticker.publishing_date is None
        assert live_ticker.topics == []
        assert live_ticker.images == []
        assert live_ticker.free_access is False

    def test_view(self):
        extraction = {
            "authors": ["Author1", "Author2", "Author3"],
            "title": "<TITLE>",
        }

        live_ticker = LiveTicker(**extraction, html=html, exception=None)

        assert live_ticker.title == "<TITLE>"
        assert sorted(live_ticker.authors) == ["Author1", "Author2", "Author3"]

    def test_extraction_view_getter(self):
        extraction = {"test_attribute": "test_value"}

        live_ticker = LiveTicker(**extraction, html=html, exception=None)

        assert live_ticker.test_attribute
        assert live_ticker.test_attribute == "test_value"

        live_ticker.__extraction__["test_attribute"] = "very_secret_stuff"  # type: ignore[index]

        assert live_ticker.test_attribute == "very_secret_stuff"

    def test_extraction_view_setter(self):
        extraction = {"test_attribute": "test_value"}

        live_ticker = LiveTicker(**extraction, html=html, exception=None)
        with pytest.raises(AttributeError):
            live_ticker.test_attribute = "another_value"

    def test_body(self):
        body = LiveTickerBody(summary=TextSequence(["Summary"]), entries=[build_entry()])

        assert LiveTicker(body=body, html=html).body is body

    def test_authors_include_entry_authors(self):
        body = LiveTickerBody(
            summary=TextSequence([]),
            entries=[build_entry(authors=["Author2"]), build_entry(authors=["Author3"])],
        )

        live_ticker = LiveTicker(authors=["Author1"], body=body, html=html)

        assert sorted(live_ticker.authors) == ["Author1", "Author2", "Author3"]

    def test_authors_are_unique(self):
        body = LiveTickerBody(summary=TextSequence([]), entries=[build_entry(authors=["Author"])] * 2)

        assert LiveTicker(authors=["Author"], body=body, html=html).authors == ["Author"]

    def test_images_include_entry_images(self):
        first, second = build_image("https://example.com/1.jpg"), build_image("https://example.com/2.jpg")
        body = LiveTickerBody(
            summary=TextSequence([]),
            entries=[build_entry(images=[first]), build_entry(images=[second])],
        )

        assert LiveTicker(images=[], body=body, html=html).images == [first, second]

    def test_images_are_not_duplicated(self):
        image = build_image()
        body = LiveTickerBody(summary=TextSequence([]), entries=[build_entry(images=[image])])

        # the page's images already contain the image of the entry
        assert LiveTicker(images=[image], body=body, html=html).images == [image]

    def test_images_do_not_accumulate(self):
        image = build_image()
        body = LiveTickerBody(summary=TextSequence([]), entries=[build_entry(images=[image])])
        live_ticker = LiveTicker(images=[], body=body, html=html)

        assert live_ticker.images == live_ticker.images == [image]

    def test_authors_and_images_without_live_ticker_body(self):
        body = ArticleBody(summary=TextSequence([]), sections=[])

        live_ticker = LiveTicker(authors=["Author"], images=[], body=body, html=html)

        assert live_ticker.authors == ["Author"]
        assert live_ticker.images == []

    def test_plaintext(self):
        body = LiveTickerBody(summary=TextSequence(["Summary"]), entries=[build_entry(paragraphs=["Entry text"])])

        plaintext = LiveTicker(body=body, html=html).plaintext

        assert plaintext is not None
        assert "Entry text" in plaintext

    def test_iter(self):
        body = LiveTickerBody(
            summary=TextSequence(["Summary"]),
            entries=[
                build_entry("Headline", ["First"], authors=["Author"], publishing_date=datetime.datetime(2025, 1, 1)),
                build_entry("", ["Second"], publishing_date=datetime.datetime(2025, 1, 2)),
            ],
        )

        entries = list(LiveTicker(body=body, html=html))

        assert len(entries) == 2
        assert all(isinstance(entry, Article) for entry in entries)

        assert entries[0].title == "Headline"
        assert entries[0].authors == ["Author"]
        assert entries[0].publishing_date == datetime.datetime(2025, 1, 1)
        assert entries[0].plaintext == "Headline\n\nFirst"

        # entries without a headline get a generic title
        assert entries[1].title == "LiveTicker Entry #2"
        assert entries[1].publishing_date == datetime.datetime(2025, 1, 2)

    def test_iter_uses_html_of_entry(self):
        body = LiveTickerBody(summary=TextSequence([]), entries=[build_entry(paragraphs=["First"])])

        (entry,) = LiveTicker(body=body, html=html)

        assert entry.html.content == "<div>First</div>"
        assert entry.html.requested_url == html.requested_url

    def test_iter_without_live_ticker_body(self):
        assert list(LiveTicker(html=html)) == []
        assert list(LiveTicker(body=ArticleBody(summary=TextSequence([]), sections=[]), html=html)) == []


class TestLiveTickerBody:
    def test_bool(self):
        assert not LiveTickerBody(summary=TextSequence(["Summary"]), entries=[])
        assert not LiveTickerBody(summary=TextSequence([]), entries=[build_entry(paragraphs=[])])
        assert LiveTickerBody(summary=TextSequence([]), entries=[build_entry()])

    def test_serialization(self):
        body = LiveTickerBody(
            summary=TextSequence(["Summary"]),
            entries=[build_entry("Headline", authors=["Author"], images=[build_image()])],
        )

        assert LiveTickerBody.deserialize(body.serialize()) == body

    def test_entry_serialization(self):
        entry = build_entry("Headline", ["First", "Second"], authors=["Author"], images=[build_image()])

        assert entry.publishing_date is not None
        assert entry.serialize()["publishing_date"] == entry.publishing_date.isoformat()

        deserialized = LiveTickerEntry.deserialize(entry.serialize())
        assert deserialized == entry
        assert deserialized.html == entry.html

    def test_entry_without_publishing_date_serialization(self):
        entry = LiveTickerEntry(sections=[], publishing_date=None, authors=[], images=[], html="")

        assert LiveTickerEntry.deserialize(entry.serialize()) == entry

    def test_entry_bool(self):
        assert not LiveTickerEntry(sections=[], publishing_date=None, authors=[], images=[], html="")
        assert build_entry()

    def test_html_is_ignored_in_comparison(self):
        first, second = build_entry(), build_entry()
        second.html = "<p>different</p>"

        assert first == second


class TestExtractLiveTickerBody:
    page = """
    <html><body>
    <div class="entry">
      <p>First</p>
      <figure><img src="https://example.com/1.jpg"><figcaption>Caption 1</figcaption></figure>
      <figure><img src="https://example.com/2.jpg"><figcaption>Caption 2</figcaption></figure>
    </div>
    <div class="entry">
      <p>Second</p>
    </div>
    <div class="entry">
      <p>Third</p>
      <figure><img src="https://example.com/3.jpg"><figcaption>Caption 3</figcaption></figure>
    </div>
    </body></html>
    """

    def test_images_are_assigned_to_their_entry(self):
        body = extract_live_ticker_body_with_selector(
            lxml.html.fromstring(self.page),
            paragraph_selector=XPath("//p"),
            entry_boundary_selector=XPath("//div[@class='entry']"),
            image_selector=XPath("//figure//img"),
        )

        first, second, third = body.entries

        assert [image.caption for image in first.images] == ["Caption 1", "Caption 2"]
        assert second.images == []
        assert [image.caption for image in third.images] == ["Caption 3"]

    def test_image_positions_are_ordered(self):
        body = extract_live_ticker_body_with_selector(
            lxml.html.fromstring(self.page),
            paragraph_selector=XPath("//p"),
            entry_boundary_selector=XPath("//div[@class='entry']"),
            image_selector=XPath("//figure//img"),
        )

        positions = [image.position for entry in body.entries for image in entry.images]

        assert positions == sorted(positions)
        assert len(set(positions)) == 3

    def test_without_image_selector(self):
        body = extract_live_ticker_body_with_selector(
            lxml.html.fromstring(self.page),
            paragraph_selector=XPath("//p"),
            entry_boundary_selector=XPath("//div[@class='entry']"),
        )

        assert all(entry.images == [] for entry in body.entries)
