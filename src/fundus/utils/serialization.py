from typing import Dict, List, Union

from typing_extensions import TypeAlias

JSONVal: TypeAlias = Union[None, bool, str, float, int, List["JSONVal"], Dict[str, "JSONVal"]]
