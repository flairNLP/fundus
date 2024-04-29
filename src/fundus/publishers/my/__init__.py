from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.publishers.my.the_sun import TheSunParser
from fundus.scraping.url import NewsMap, Sitemap
class MY(PublisherEnum):
    TheSun = PublisherSpec(
        name="The Sun",
        domain="https://www.thesun.my/",
        sources=[Sitemap("https://thesun.my/sitemap.xml"),
                 NewsMap("https://thesun.my/sitemapforgoogle.xml")],
        parser=TheSunParser,
    )