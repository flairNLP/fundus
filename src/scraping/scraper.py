from typing import Literal

from src.parser.html_parser import BaseParser
from src.scraping.article import Article
from src.scraping.crawler.crawler import Crawler


class Scraper:

    def __init__(self,
                 *sources: Crawler,
                 parser: BaseParser):

        self.crawler = list(sources)
        self.parser = parser

    def scrape(self, error_handling: Literal['suppress', 'catch', 'raise']):
        for crawler in self.crawler:
            for article_source in crawler.crawl():

                try:

                    data = self.parser.parse(article_source.html, error_handling)

                except Exception as err:

                    if error_handling == 'raise':
                        raise err
                    elif error_handling == 'catch':
                        yield Article(extracted={}, exception=err, **article_source.serialize())
                        continue
                    elif error_handling == 'suppress':
                        continue
                    else:
                        raise ValueError(f"Unknown value '{error_handling}' for parameter <error_handling>'")

                article = Article(extracted=data, **article_source.serialize())
                yield article
