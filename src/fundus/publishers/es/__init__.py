import datetime

from dateutil.rrule import MONTHLY, rrule

from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.es.el_pais import ElPaisParser
from fundus.scraping.url import RSSFeed, Sitemap


class ES(metaclass=PublisherGroup):
    ElPais = Publisher(
        name="El País",
        domain="https://elpais.com/",
        parser=ElPaisParser,
        sources=[RSSFeed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada")]
        + [
            Sitemap(f"https://elpais.com/sitemaps/{d.year}/{str(d.month).zfill(2)}/sitemap_0.xml")
            for d in reversed(
                list(rrule(MONTHLY, dtstart=datetime.datetime(1976, 5, 1), until=datetime.datetime.now()))
            )
        ],
    )
