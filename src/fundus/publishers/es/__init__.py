import datetime

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
            Sitemap(f"https://elpais.com/sitemaps/{datetime.datetime.now().year}/{month:02d}/sitemap_0.xml")
            for month in range(datetime.datetime.now().month, 0, -1)
        ]
        + [
            Sitemap(f"https://elpais.com/sitemaps/{year}/{month:02d}/sitemap_0.xml")
            for year in range(datetime.datetime.now().year - 1, 1976, -1)
            for month in range(12, 0, -1)
        ]
        + [Sitemap(f"https://elpais.com/sitemaps/1976/{month:02d}/sitemap_0.xml") for month in range(12, 4, -1)],
    )
