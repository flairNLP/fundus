from fundus.publishers.base_objects import Publisher, PublisherGroup

from .wikinews import EDITIONS, WikinewsAPI, WikinewsParser


class INTERNATIONAL(metaclass=PublisherGroup):
    """Publishers without a single country of origin."""

    default_language = "en"

    # Wikinews is modelled as a single publisher rather than one publisher per edition:
    # the editions share an editorial project, a license and a terms of use, and one
    # publisher means the crawler opens one thread against WMF infrastructure instead of
    # one per subdomain. Each edition contributes a language-tagged source, so a single
    # edition is reached with the crawler's <language_filter> rather than by name.
    Wikinews = Publisher(
        name="Wikinews",
        # The portal redirects to en.wikinews.org, whose robots.txt is the reference
        # ruleset for every edition.
        domain="https://www.wikinews.org",
        parser=WikinewsParser,
        sources=[WikinewsAPI(language) for language in EDITIONS],
    )
