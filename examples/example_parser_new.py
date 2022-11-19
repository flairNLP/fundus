import re
from typing import List

import feedparser
import lxml
import requests

from src.crawler.crawler import Crawler
from src.library.collection import PublisherCollection


def download_urls_from_sitemap(sitemap_url: str) -> List[str]:
    sitemap_html = requests.get(sitemap_url).content
    sitemap_tree = lxml.html.fromstring(sitemap_html)
    url_nodes = sitemap_tree.cssselect('url > loc')
    sitemap_urls = {node.text_content() for node in url_nodes}

    return sorted(list(sitemap_urls))


def download_urls_from_rss(rss_url: str) -> List[str]:
    rss_feed = feedparser.parse(rss_url)
    initial_urls = {entry["link"] for entry in rss_feed['entries']}
    cleaned_urls = {re.sub('#ref=rss', '', url_el) for url_el in initial_urls}
    return sorted(list(cleaned_urls))


def test_welt_parser():

    # not intuitive, ...
    de_de = PublisherCollection.de_de

    crawler = Crawler(de_de.DieWelt)
    for article in crawler.crawl(max_articles=100, error_handling='raise'):
        print(article.pprint(exclude=['html']))


if __name__ == '__main__':
    test_welt_parser()