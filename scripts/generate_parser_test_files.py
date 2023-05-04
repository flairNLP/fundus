import json
import subprocess
from argparse import ArgumentParser
from logging import WARN
from os.path import exists
from typing import List, Optional

from tqdm import tqdm

from fundus import Crawler, PublisherCollection
from fundus.logging.logger import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from tests.utility import HTMLFile, generate_json_path, load_html_mapping, load_json


def get_test_article(enum: PublisherEnum) -> Optional[Article]:
    crawler = Crawler(enum)
    return next(crawler.crawl(max_articles=1, error_handling="suppress", only_complete=True), None)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="generate_parser_test_files",
        description=(
            "script to generate/update/overwrite test cases for parser unit tests. "
            "by default this will only generate files which do not exist yet"
        ),
    )
    parser.add_argument(
        "attributes",
        metavar="Attr",
        nargs="+",
        help="the attributes which should be used to create test cases",
    )
    parser.add_argument("-p", "--publishers", nargs="+", help="only consider given publishers")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="overwrite existing html and json " "files for the latest version",
    )
    group.add_argument(
        "-u", "--update", action="store_true", help="parse from existing html and only update json content"
    )
    group.add_argument(
        "-uf", action="store_true", help="parse from existing html and overwrite existing content in json"
    )

    args = parser.parse_args()

    basic_logger.setLevel(WARN)

    publishers: List[PublisherEnum] = (
        [pub for pub in PublisherCollection if pub.name in args.publisher]
        if args.publisher
        else list(PublisherCollection)
    )

    bar = tqdm(total=len(publishers))

    for publisher in publishers:
        bar.set_description(desc=publisher.name, refresh=True)
        bar.update(1)

        # load json
        json_path = generate_json_path(publisher)
        # ensure directories are there
        json_path.parent.mkdir(parents=True, exist_ok=True)
        if exists(generate_json_path(publisher)):
            json_data = load_json(publisher)
        else:
            json_data = {}

        # load html
        html_mapping = load_html_mapping(publisher)

        if args.update or args.uf:
            for html in html_mapping.values():
                version = html.publisher.parser(html.crawl_date)
                extraction = version.parse(html.content)
                entry = json_data[type(version).__name__]
                new = {attr: value for attr, value in extraction.items() if attr in args.attributes}
                if args.update:
                    entry["content"].update(new)
                elif args.uf:
                    entry["content"] = new

        elif args.overwrite or not html_mapping.get(publisher.parser.latest_version):
            if not (article := get_test_article(publisher)):
                basic_logger.warn(f"Couldn't get article for {publisher.name}. Skipping")
                continue
            html = HTMLFile(content=article.source.html, crawl_date=article.source.crawl_date, publisher=publisher)
            html.write()

            meta = {"url": article.source.url, "crawl_date": str(article.source.crawl_date)}
            requested_attrs = set(args.attributes)
            content = {attr: value for attr in args.attributes if (value := article.__dict__.get(attr))}
            entry = {"meta": meta, "content": content}
            json_data.update({publisher.parser.latest_version.__name__: entry})

            subprocess.call(["git", "add", html.path], stdout=subprocess.PIPE)

        with open(json_path, "w+", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, indent=4, ensure_ascii=False)

        subprocess.call(["git", "add", json_path], stdout=subprocess.PIPE)
