"""
This script performs a baseline real-time crawler validation for every publisher and reports the test coverage.
The tests include a real-time crawl for each publisher's news map and RSS Feed
checking the received articles for attribute completeness.
Note that this script does not check the attributes' correctness, only their presence.
"""

import sys
import traceback
from argparse import ArgumentParser
from typing import List, Optional

from fundus import Crawler, PublisherCollection
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.article import Article
from fundus.scraping.session import session_handler


def main() -> None:
    failed: int = 0
    timeout_in_seconds: int = 30

    argument_parser = ArgumentParser()
    argument_parser.add_argument(
        "-s",
        "--skip",
        default=[],
        nargs="*",
        help="List of publishers to skip. Expects Fundus attribute names.",
    )
    parsed_arguments = argument_parser.parse_args()

    publisher_regions: List[PublisherGroup] = sorted(
        PublisherCollection.get_subgroup_mapping().values(), key=lambda region: region.__name__
    )

    with session_handler.context(timeout=timeout_in_seconds):
        for publisher_region in publisher_regions:
            print(f"{publisher_region.__name__:-^50}")

            publisher: Publisher
            for publisher in sorted(publisher_region, key=lambda p: p.name):
                publisher_name: str = publisher.name

                if not any(publisher.source_mapping.values()):
                    # skip publishers providing no sources for forward crawling
                    print(f"⏩  SKIPPED: {publisher_name!r} - No sources defined")
                    continue
                if publisher.deprecated:  # type: ignore[attr-defined]
                    print(f"⏩  SKIPPED: {publisher_name!r} - Deprecated")
                    continue
                if publisher.__name__ in parsed_arguments.skip:
                    print(f"⏩  SKIPPED: {publisher_name!r} - Blocked")
                    continue
                crawler: Crawler = Crawler(publisher, delay=0.4, ignore_robots=True)

                complete_article: Optional[Article] = next(
                    crawler.crawl(max_articles=1, timeout=timeout_in_seconds, only_complete=True),
                    None,
                )

                if complete_article is None:
                    try:
                        incomplete_article: Optional[Article] = next(
                            crawler.crawl(
                                max_articles=1, timeout=timeout_in_seconds, only_complete=False, raise_on_error=True
                            ),
                            None,
                        )
                    except Exception as exception:
                        print(f"❌ FAILED: {publisher_name!r} - Encountered exception during crawling")
                        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stdout)
                        failed += 1
                        continue

                    if incomplete_article is None:
                        print(f"❌ FAILED: {publisher_name!r} - No articles received")

                    else:
                        print(
                            f"❌ FAILED: {publisher_name!r} - No complete articles received "
                            f"(URL of an incomplete article: {incomplete_article.html.requested_url}) with attributes:\n"
                            f"title: {incomplete_article.title is not None}\n"
                            f"plaintext: {bool(incomplete_article.body)}\n"
                            f"publishing_date: {incomplete_article.publishing_date is not None}\n"
                            f"authors: {bool(incomplete_article.authors)}\n"
                            f"topics: {bool(incomplete_article.topics)}\n"
                            f"images: {bool(incomplete_article.images)}\n"
                        )
                    failed += 1
                    continue

                print(f"✔️ PASSED: {publisher_name!r}")
            print()

    total_publishers: int = len(PublisherCollection)
    pass_ratio: str = f"{total_publishers - failed}/{total_publishers}"
    if failed:
        print(f"🚨 {pass_ratio} - Some publishers finished in a 'FAILED' state")
    else:
        print(f"✨ {pass_ratio} - All publishers passed the tests")

    exit(-1 if failed else 0)


if __name__ == "__main__":
    main()
