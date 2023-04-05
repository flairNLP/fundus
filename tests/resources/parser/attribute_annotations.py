from datetime import datetime
from typing import Dict, List, Optional, Union

from src.parsing import ArticleBody

attribute_annotation_mapping: Dict[str, Union[type, object]] = {
    "title": Optional[str],
    "body": ArticleBody,
    "authors": List[str],
    "publishing_date": Optional[datetime],
    "topics": List[str],
}
