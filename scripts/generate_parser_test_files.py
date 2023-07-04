import subprocess
from argparse import ArgumentParser
from logging import WARN
from typing import List, Optional

from tqdm import tqdm

from fundus import Crawler, PublisherCollection
from fundus.logging import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from tests.utility import HTMLTestFile, get_test_case_json, load_html_test_file_mapping


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
        help="overwrite existing html and json files for the latest parser version",
    )
    group.add_argument(
        "-oj",
        "--overwrite_json",
        action="store_true",
        help="parse from existing html and overwrite existing json content",
    )

    args = parser.parse_args()

    # sort args.attributes for consistency
    args.attributes = list(sorted(args.attributes))

    basic_logger.setLevel(WARN)

    publishers: List[PublisherEnum] = (
        list(PublisherCollection)
        if args.publishers is None
        else [pub for pub in PublisherCollection if pub.name in args.publishers]
    )

    with tqdm(total=len(publishers)) as bar:
        for publisher in publishers:
            bar.set_description(desc=publisher.name, refresh=True)

            # load json
            test_data_file = get_test_case_json(publisher)
            test_data = content if (content := test_data_file.load()) and not args.overwrite_json else {}

            # load html
            html_mapping = load_html_test_file_mapping(publisher) if not args.overwrite else {}

            if args.overwrite or not html_mapping.get(publisher.parser.latest_version):
                if not (article := get_test_article(publisher)):
                    basic_logger.warn(f"Couldn't get article for {publisher.name}. Skipping")
                    continue
                html = HTMLTestFile(
                    url=article.html.responded_url,
                    content=article.html.content,
                    crawl_date=article.html.crawl_date,
                    publisher=publisher,
                )
                html.write()
                subprocess.call(["git", "add", html.path], stdout=subprocess.PIPE)

                html_mapping[publisher.parser.latest_version] = html
                test_data[publisher.parser.latest_version.__name__] = {}

            for html in html_mapping.values():
                versioned_parser = html.publisher.parser(html.crawl_date)
                extraction = versioned_parser.parse(html.content)
                new = {attr: value for attr, value in extraction.items() if attr in args.attributes}
                if not (entry := test_data.get(type(versioned_parser).__name__)):
                    test_data[type(versioned_parser).__name__] = new
                else:
                    entry.update(new)

            test_data_file.write(test_data)
            bar.update()
            subprocess.call(["git", "add", test_data_file.path], stdout=subprocess.PIPE)

        bar.update()
