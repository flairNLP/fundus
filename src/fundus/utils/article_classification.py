import re
from typing import Any, Callable, Optional


def url_based_classifier(regex: str) -> Callable[..., Any]:
    def result_func(html: str, url: str):
        return bool(re.search(regex, url))

    return result_func
