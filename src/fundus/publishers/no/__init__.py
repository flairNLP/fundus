from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap
from fundus.scraping.filter import inverse, regex_filter

from .verdensgang import VerdensGangParser
from .dagbladet import DagbladetParser
from .nettavisen import NettavisenParser
from .norskrikskringkastning import NRKParser



class NO(metaclass=PublisherGroup):
    VerdensGang = Publisher(
        name="VG",
        domain="https://www.vg.no/",
        parser=VerdensGangParser,
        sources=[
            Sitemap("https://www.vg.no/sitemap.xml",
                    sitemap_filter=inverse(regex_filter("vg\.no\/sitemaps/\d{4}\-\d{2}-articles.xml")), 
                    reverse=True),
            NewsMap("https://www.vg.no/sitemap/files/articles-48hrs.xml"),
        ]
    )

    Dagbladet = Publisher(
        name="Dagbladet",
        domain="https://www.db.no/",
        parser=DagbladetParser,
        sources=[
            Sitemap("https://www.dagbladet.no/app/jw-api-proxy/sitemap/index/dagbladet.xml", reverse=True),
            NewsMap("https://www.dagbladet.no/sitemap"),
        ]
    )

    Nettavisen = Publisher(
        name="Nettavisen",
        domain="https://www.nettavisen.no/",
        parser=NettavisenParser,
        sources=[
            RSSFeed("https://www.nettavisen.no/service/rich-rss"),
        ]
    )

    NRK = Publisher(
        name="NRK",
        domain="https://www.nrk.no/",
        parser=NRKParser,
        sources=[
            RSSFeed("https://www.nrk.no/norge/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/urix/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/sport/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/kultur/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/livsstil/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/viten/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/dokumentar/toppsaker.rss")
        ]
    )