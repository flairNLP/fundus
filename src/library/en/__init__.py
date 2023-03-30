from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from src.library.en.washington_times_parser import WashingtonTimesParser


class EN(PublisherEnum):
    WashingtonTimes = PublisherSpec(
        domain="https://www.washingtontimes.com/",
        rss_feeds=["https://www.washingtontimes.com/rss/headlines/news/politics/"],
        parser=WashingtonTimesParser,
    )
