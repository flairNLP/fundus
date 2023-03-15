from src.library.collection.base_objects import PublisherEnum, PublisherSpec

from .orf_parser import OrfParser


# noinspection PyPep8Naming
class AT_AT(PublisherEnum):
    ORF = PublisherSpec(
        domain="https://www.orf.at",
        rss_feeds=["https://rss.orf.at/news.xml"],
        sitemaps=[],
        parser=OrfParser,
    )
