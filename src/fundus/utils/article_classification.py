import re
from typing import Any, Callable, Optional


def url_based_classifier(
    confirming_regex: Optional[str] = None, rejecting_regex: Optional[str] = None
) -> Callable[..., Any]:
    if not confirming_regex and not rejecting_regex:
        print("One of the values 'confirming regex' and 'rejecting regex' has to be set!")
        exit()

    def result_func(html: str, url: str):
        is_accepted = False
        is_rejected = True
        if confirming_regex:
            is_accepted = bool(re.search(confirming_regex, url))
        if rejecting_regex:
            is_rejected = bool(re.search(rejecting_regex, url))

        if is_rejected and is_accepted:
            print("Url cant be both rejected and accepted!")
            exit()

        if is_accepted and not is_rejected:
            return True
        if is_rejected and not is_accepted:
            return False
        if not is_rejected and not is_accepted:
            return True

    return result_func
