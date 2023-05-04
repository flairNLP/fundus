import json
import subprocess
from argparse import ArgumentParser
from logging import WARN
from typing import List, Optional

from tqdm import tqdm

from fundus import Crawler, PublisherCollection
from fundus.logging.logger import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from tests.utility import (
    HTMLTestFile,
    generate_parser_test_case_json_path,
    load_html_test_file_mapping,
    load_test_case_data,
)


def get_test_article(enum: PublisherEnum) -> Optional[Article]:
    crawler = Crawler(enum)
    return next(crawler.crawl(max_articles=1, error_handling="suppress", only_complete=True), None)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="generate_parser_test_files",
        description=(
            "script to generate/update/overwrite test cases for parser unit tests. "
            "by default this will only generate files which do not exist yet. "
            "every changed/added file will automatically be added to git."
        ),
    )
    parser.add_argument(
        "attributes",
        metavar="A",
        nargs="+",
        help="the attributes which should be used to create test cases",
    )
    parser.add_argument("-p", dest="publishers", metavar="P", nargs="+", help="only consider given publishers")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="overwrite existing html and json files for the latest version",
    )
    group.add_argument(
        "-u", "--update", action="store_true", help="parse from existing html and only update json content"
    )
    group.add_argument(
        "-oj", "--overwrite_json", action="store_true", help="parse from existing html and overwrite existing json"
    )

    args = parser.parse_args()

    basic_logger.setLevel(WARN)

    publishers: List[PublisherEnum] = (
        list(PublisherCollection)
        if args.publishers is None
        else [pub for pub in PublisherCollection if pub.name in args.publishers]
    )

    with tqdm(total=len(publishers)) as bar:
        for publisher in publishers:
            bar.set_description(desc=publisher.name, refresh=True)
            bar.update()

            # load json
            json_path = generate_parser_test_case_json_path(publisher)
            # ensure directories are there
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_data = load_test_case_data(publisher) if json_path.exists() else {}

            # load html
            html_mapping = load_html_test_file_mapping(publisher)

            if args.update or args.overwrite_json:
                for html in html_mapping.values():
                    version = html.publisher.parser(html.crawl_date)
                    extraction = version.parse(html.content)
                    # TODO: overwrite entire json when -oj
                    entry = json_data[type(version).__name__]
                    new = {attr: value for attr, value in extraction.items() if attr in args.attributes}
                    if args.update:
                        entry["content"].update(new)
                    elif args.overwrite_json:
                        entry["content"] = new

            elif args.overwrite or not html_mapping.get(publisher.parser.latest_version):
                if not (article := get_test_article(publisher)):
                    basic_logger.warn(f"Couldn't get article for {publisher.name}. Skipping")
                    continue
                html = HTMLTestFile(
                    content=article.source.html, crawl_date=article.source.crawl_date, publisher=publisher
                )
                html.write()

                metadata = {"url": article.source.url, "crawl_date": str(article.source.crawl_date)}
                requested_attrs = set(args.attributes)
                content = {attr: value for attr in args.attributes if (value := getattr(article, attr, None))}
                entry = {"meta": metadata, "content": content}
                json_data.update({publisher.parser.latest_version.__name__: entry})

                subprocess.call(["git", "add", html.path], stdout=subprocess.PIPE)

            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(json_data, json_file, indent=4, ensure_ascii=False)
                json_file.write("\n")

            subprocess.call(["git", "add", json_path], stdout=subprocess.PIPE)
