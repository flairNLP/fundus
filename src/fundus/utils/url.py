from urllib.parse import urljoin, urlparse


def is_valid_url(url: str) -> bool:
    """True if the URL has an http/https scheme and a non-empty network location."""
    parsed = urlparse(url)
    return bool(parsed.scheme in ("http", "https") and parsed.netloc)


def strip_query_and_fragment(url: str) -> str:
    """Return the URL with its query string and fragment removed.

    Intended for *identity* use (dedup keys, equality probes), not for fetching:
    the result may resolve to a different resource than the input on servers that
    rely on query parameters for routing.
    """
    if any(indicator in url for indicator in ("?", "#")):
        return urljoin(url, urlparse(url).path)
    return url
