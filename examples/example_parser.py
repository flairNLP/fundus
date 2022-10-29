import json
from datetime import datetime
from typing import List

import lxml
import requests

from src.parser_lib.de_de.bz_parser import BZParser
from src.parser_lib.de_de.dw_parser import DWParser


def download_html_strs_from_sitemap(sitemap_url: str) -> List[str]:
    sitemap_html = requests.get(sitemap_url).content
    sitemap_tree = lxml.html.fromstring(sitemap_html)
    url_nodes = sitemap_tree.cssselect('url > loc')
    sitemap_urls = {node.text_content() for node in url_nodes}

    return sorted(list(sitemap_urls))


if __name__ == '__main__':

    example_parser = DWParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    current_sitemap = "https://www.dw.com/de/sitemap-news.xml"


    for url_el in download_html_strs_from_sitemap(current_sitemap):
        try:
            current_html = requests.get(url_el).content
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue
