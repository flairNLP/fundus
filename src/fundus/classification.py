import re
from typing import Callable, Protocol


def regex_classifier(regex: str) -> Callable[[str], bool]:
    def classify(url: str):
        return bool(re.search(regex, url))

    return classify


class UrlClassifier(Protocol):
    """Classifies a website, represented by a given <url> as an article.

    When called with (<url>), an object satisfying this protocol should return
    the truth value of a binary classification classifying the website represented with
    <url> as article or not.

    Returns: This is a binary classification, so:
        <True>:     The represented website is considered to be an article:
        <False>:    The represented website is considered not to be an article
    """

    def __call__(
            self,
            url: str,
    ) -> bool:
        ...


class HtmlClassifier(Protocol):
    """Classifies a website, represented by a given <html> as an article.

    When called with (<html>), an object satisfying this protocol should return
    the truth value of a binary classification classifying the website represented with <html> as article or not.

    Returns: This is a binary classification, so:
        <True>:     The represented website is considered to be an article:
        <False>:    The represented website is considered not to be an article
    """

    def __call__(self, url: str) -> bool:
        ...
