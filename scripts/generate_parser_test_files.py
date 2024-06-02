import subprocess
from argparse import ArgumentParser, Namespace
from logging import WARN
from typing import List, Optional, Union, Tuple

from tqdm import tqdm

from fundus import Crawler, PublisherCollection
from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.article import Article
from fundus.scraping.filter import RequiresAll
from fundus.scraping.html import WebSource
from fundus.scraping.scraper import BaseScraper
from tests.test_parser import attributes_required_to_cover
from tests.utility import HTMLTestFile, get_test_case_json, load_html_test_file_mapping

logger = create_logger(__name__)


def get_test_article(publisher: Publisher, url: Optional[str] = None) -> Optional[Article]:
    if url is not None:
        source = WebSource([url], publisher=publisher.publisher_name)
        scraper = BaseScraper(source, parser_mapping={publisher.publisher_name: publisher.parser})
        return next(scraper.scrape(error_handling="suppress", extraction_filter=RequiresAll()), None)

    crawler = Crawler(publisher)
    return next(crawler.crawl(max_articles=1, error_handling="suppress", only_complete=RequiresAll()), None)


def parse_arguments() -> Namespace:
    parser = ArgumentParser(
        prog="generate_parser_test_files",
        description=(
            "script to generate/update/overwrite test cases for parser unit tests. "
            "by default this will only generate files which do not exist yet. "
            "every changed/added file will automatically be added to git."
        ),
    )
    parser.add_argument(
        "-a",
        "--attributes",
        nargs="+",
        default=[],
        help=(
            "the attributes which should be used to create test cases. "
            f"default: {', '.join(attributes_required_to_cover)}"
        ),
    )
    parser.add_argument("-p", dest="publishers", metavar="P", nargs="+", help="only consider given publishers")
    parser.add_argument(
        "-u",
        "--urls",
        metavar="U",
        nargs="+",
        help="use given URL instead of searching for an article. if set the urls will be mapped to the order of -p",
    )
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

    arguments = parser.parse_args()

    if arguments.urls is not None:
        if arguments.publishers is None:
            parser.error("-u requires -p. you can only specify URLs when also specifying publishers.")
        if len(arguments.urls) != len(arguments.publishers):
            parser.error("-u and -p do not have the same argument length")

    return arguments


def main() -> None:
    arguments = parse_arguments()

    # sort args.attributes for consistency
    arguments.attributes = sorted(set(arguments.attributes) or attributes_required_to_cover)

    logger.setLevel(WARN)
    publishers_with_parent_groups: List[Tuple[Publisher, PublisherGroup]]
    if arguments.publishers is None:
        publishers_with_parent_groups = list(PublisherCollection.parent_iterator())
    else:
        publishers_with_parent_groups = list()
        for item in PublisherCollection.parent_iterator():
            if item[0] in arguments.publishers:
                publishers_with_parent_groups.append(item)

    urls = arguments.urls if arguments.urls is not None else [None] * len(publishers_with_parent_groups)

    with tqdm(total=len(publishers_with_parent_groups)) as bar:
        for url, element in zip(urls, publishers_with_parent_groups):
            publisher, parent_group = element
            bar.set_description(desc=publisher.publisher_name, refresh=True)

            # load json
            test_data_file = get_test_case_json(publisher, parent_group)
            test_data = content if not arguments.overwrite_json and (content := test_data_file.load()) else {}

            # load html
            html_mapping = load_html_test_file_mapping(publisher, parent_group)

            if arguments.overwrite or not html_mapping.get(publisher.parser.latest_version):
                if not (article := get_test_article(publisher, url)):
                    logger.error(f"Couldn't get article for {publisher.publisher_name}. Skipping")
                    continue
                html = HTMLTestFile(
                    url=article.html.responded_url,
                    content=article.html.content,
                    crawl_date=article.html.crawl_date,
                    publisher=publisher,
                    parent_group=parent_group
                )
                html.write()
                subprocess.call(["git", "add", html.path], stdout=subprocess.PIPE)

                # remove previous file
                if previous_file := html_mapping.get(publisher.parser.latest_version):
                    previous_file.remove()

                html_mapping[publisher.parser.latest_version] = html
                test_data[publisher.parser.latest_version.__name__] = {}

            for html in html_mapping.values():
                versioned_parser = html.publisher.parser(html.crawl_date)
                extraction = versioned_parser.parse(html.content)
                missing_attributes = set(arguments.attributes) - set(
                    test_data.get(type(versioned_parser).__name__) or {}
                )
                new = {attr: value for attr, value in extraction.items() if attr in missing_attributes}
                if not (entry := test_data.get(type(versioned_parser).__name__)):
                    test_data[type(versioned_parser).__name__] = new
                else:
                    entry.update(new)
                    test_data[type(versioned_parser).__name__] = dict(sorted(entry.items()))

            test_data_file.write(test_data)
            bar.update()
            subprocess.call(["git", "add", test_data_file.path], stdout=subprocess.PIPE)


if __name__ == "__main__":
    main()
