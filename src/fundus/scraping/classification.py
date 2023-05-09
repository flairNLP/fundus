import re
from typing import Callable


def regex_classifier(regex: str) -> Callable[[str], bool]:
    def classify(url: str):
        return bool(re.search(regex, url))

    return classify
