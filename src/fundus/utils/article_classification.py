from typing import Callable


def url_based_classifier(url_substr: str) -> Callable:
    def result_func(html:str, url:str):
        return url_substr in url

    return result_func
