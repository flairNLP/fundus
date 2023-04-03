import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Union

import lxml.html

from doc import docs_path


# noinspection PyUnresolvedReferences
@lru_cache
def parse_annotations() -> Dict[str, Union[type, object]]:
    # There is no need to import these objects locally rather than globally, but we need to import them nonetheless.
    # We do it locally to get noinspection for the function scope
    # We have to so eval() can link the objects
    from datetime import datetime
    from typing import Optional

    from src.parser.html_parser import ArticleBody

    local_ns = locals()

    relative_path = Path("attribute_guidelines.md")
    attribute_guidelines_path = os.path.join(docs_path, relative_path)

    with open(attribute_guidelines_path, "rb") as file:
        content = file.read()

    root = lxml.html.fromstring(content)
    row_nodes: List[lxml.html.HtmlElement] = root.xpath("//tr[position() > 1]")
    rows = [tuple(child.text_content() for child in node.iterchildren()) for node in row_nodes]
    return {name: eval(annotation, globals(), local_ns) for name, _, annotation in rows}
