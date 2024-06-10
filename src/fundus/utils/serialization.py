from typing import Dict, Sequence, Union

from typing_extensions import TypeAlias

JSONVal: TypeAlias = Union[None, bool, str, float, int, Sequence["JSONVal"], Dict[str, "JSONVal"]]
