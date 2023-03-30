from datetime import datetime
from typing import Dict, List, Optional, Union

from src.parser.html_parser import ArticleBody

attribute_annotations: Dict[str, Union[type, object]] = {
    "title": Optional[str],
    "body": ArticleBody,
    "authors": List[str],
    "publishing_date": Optional[datetime],
    "topics": List[str],
}
