"""
This script performs a baseline real-time crawler validation for every publisher and reports the test coverage.
The tests include a real-time crawl for each publisher's news map and RSS Feed
checking the received articles for attribute completeness.
Note that this script does not check the attributes' correctness, only their presence.
"""
import sys
import traceback
from typing import List, Optional, cast

from fundus import Crawler, PublisherCollection
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.article import Article
from fundus.scraping.filter import RequiresAll
from scripts.utility import timeout


def main() -> None:
    failed: int = 0

    publisher_regions: List[PublisherGroup] = sorted(
        PublisherCollection.get_subgroup_mapping().values(), key=lambda region: region.__name__
    )

    for publisher_region in publisher_regions:
        print(f"{publisher_region.__name__:-^50}")

        publisher: Publisher
        for publisher in sorted(publisher_region, key=lambda p: p.name):
            publisher_name: str = publisher.name

            if not any(publisher.source_mapping.values()):  # type: ignore[attr-defined]
                # skip publishers providing no sources for forward crawling
                print(f"⏩  SKIPPED: {publisher_name!r} - No sources defined")
                continue

            crawler: Crawler = Crawler(publisher, delay=0.4)

            timed_next = timeout(next, time=20, silent=True)

            complete_article: Optional[Article] = timed_next(  # type: ignore[call-arg]
                crawler.crawl(max_articles=1, only_complete=RequiresAll(), error_handling="suppress"), None
            )

            if complete_article is None:
                incomplete_article: Optional[Article] = timed_next(  # type: ignore[call-arg]
                    crawler.crawl(max_articles=1, only_complete=False, error_handling="catch"), None
                )

                if incomplete_article is None:
                    print(f"❌ FAILED: {publisher_name!r} - No articles received")

                elif incomplete_article.exception is not None:
                    print(
                        f"❌ FAILED: {publisher_name!r} - Encountered exception during crawling "
                        f"(URL: {incomplete_article.html.requested_url})"
                    )
                    traceback.print_exception(
                        etype=type(incomplete_article.exception),
                        value=incomplete_article.exception,
                        tb=incomplete_article.exception.__traceback__,
                        file=sys.stdout,
                    )

                else:
                    print(
                        f"❌ FAILED: {publisher_name!r} - No complete articles received "
                        f"(URL of an incomplete article: {incomplete_article.html.requested_url})"
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

    exit(failed)


if __name__ == "__main__":
    main()
