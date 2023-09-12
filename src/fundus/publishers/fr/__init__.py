from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.publishers.fr.le_monde import LeMondeParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.html import NewsMap, Sitemap


class FR(PublisherEnum):
    LeMonde = PublisherSpec(
        name="Le Monde",
        domain="https://www.lemonde.fr/",
        sources=[NewsMap("https://www.lemonde.fr/sitemap_news.xml")],
        parser=LeMondeParser,
    )
