from dataclasses import dataclass


@dataclass
class SourceUrl:
    url: str


@dataclass
class RSSFeed(SourceUrl):
    pass


@dataclass
class Sitemap(SourceUrl):
    recursive: bool = True
    reverse: bool = False


@dataclass
class NewsMap(Sitemap):
    pass
