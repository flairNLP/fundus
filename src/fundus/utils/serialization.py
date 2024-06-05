from typing import Dict, List, Union

from typing_extensions import TypeAlias

JSONPrimitives: TypeAlias = Union[None, bool, str, float, int]
# List[JSONPrimitives] is not valid, hence this work around. See https://github.com/python/mypy/issues/3351 for details
JSONVal: TypeAlias = Union[JSONPrimitives, List[bool], List[str], List[float], List[int], Dict[str, JSONPrimitives]]
