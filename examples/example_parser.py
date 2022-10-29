import json
import re
from typing import List

import feedparser
import lxml
import requests

from src.parser_lib.de_de.focus_parser import FocusParser


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


if __name__ == '__main__':

    example_parser = FocusParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.dw.com/de/sitemap-news.xml"
    current_rss = "https://rss.focus.de/fol/XML/rss_folnews.xml"

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).content
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue
