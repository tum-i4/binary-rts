from itertools import chain
from typing import Iterable, Any, Dict, List


def dict_equals(dict1: Dict, dict2: Dict) -> bool:
    if set(dict1.keys()) != set(dict2.keys()):
        return False
    if set(flatten_dict_values(dict1)) != set(flatten_dict_values(dict2)):
        return False
    return True


def flatten_dict_values(dictionary: Dict[Any, Iterable[Any]]) -> List[Any]:
    return list(chain.from_iterable(dictionary.values()))
