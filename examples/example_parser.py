import json
import re
from typing import List

import feedparser
import lxml
import requests

from src.parser_lib.de_de.die_welt_parser import DieWeltParser
from src.parser_lib.de_de.dw_parser import DWParser
from src.parser_lib.de_de.focus_parser import FocusParser
from src.parser_lib.de_de.mdr_parser import MDRParser
from src.parser_lib.de_de.merkur_parser import MerkurParser
from src.parser_lib.de_de.ndr_parser import NDRParser


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
    example_parser = DieWeltParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.ndr.de/sitemap112-newssitemap.xml"
    current_rss = "https://www.welt.de/feeds/latest.rss"

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_dw_parser():
    example_parser = DWParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.dw.com/de/sitemap-news.xml"
    current_rss = "https://www.welt.de/feeds/latest.rss"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_focus_parser():
    example_parser = FocusParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.dw.com/de/sitemap-news.xml"
    current_rss = 'https://rss.focus.de/fol/XML/rss_folnews.xml'

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_mdr_parser():
    example_parser = MDRParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.mdr.de/news-sitemap.xml"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_merkur_parser():
    example_parser = MerkurParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_rss = "https://www.merkur.de/welt/rssfeed.rdf"

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue

def test_ndr_parser():
    example_parser = NDRParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.ndr.de/sitemap112-newssitemap.xml"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue

if __name__ == '__main__':
    test_ndr_parser()

