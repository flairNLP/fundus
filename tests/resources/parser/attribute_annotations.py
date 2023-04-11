import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import lxml.html

from doc import docs_path


# noinspection PyUnresolvedReferences
def _parse_attribute_annotations() -> Dict[str, object]:
    """Returns a dictionary of the parser's attribute type guidelines mapping from the attribute's name to its type."""

    # We import the attribute annotations types locally to make them accessible in the local namespace,
    # such that eval() can evaluate the type annotations.
    # Therefore, these imports are not unused and manageable more easily than defining them in the global namespace.
    from datetime import datetime
    from typing import Optional

    from src.parser.html_parser import ArticleBody

    relative_path = Path("attribute_guidelines.md")
    attribute_guidelines_path = os.path.join(docs_path, relative_path)

    with open(attribute_guidelines_path, "rb") as file:
        attribute_guidelines: bytes = file.read()

    root = lxml.html.fromstring(attribute_guidelines)
    row_nodes: List[lxml.html.HtmlElement] = root.xpath("//table[@class='annotations']/tr[position() > 1]")
    rows: List[Tuple[str, ...]] = [tuple(child.text_content() for child in node.iterchildren()) for node in row_nodes]
    assert rows and all(len(row) == 3 for row in rows), (
        "The annotation guideline table is expected to have exactly three columns: " "'Name', 'Description' and 'Type'."
    )

    local_ns: Dict[str, Any] = locals()
    return {name: eval(annotation, globals(), local_ns) for name, _, annotation in rows}


attribute_annotations_mapping = _parse_attribute_annotations()
