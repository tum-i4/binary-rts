import math
from typing import List, Any


def array_split(array: List[Any], num_arrays: int) -> List[List[Any]]:
    """Splits a given ``array`` into ``num_arrays`` sub-arrays."""
    if num_arrays <= 1:
        return [array]
    arrays: List[List[Any]] = []
    rem_len: int = len(array)
    rem_num_arrays: int = num_arrays
    curr_start_idx: int = 0
    while rem_num_arrays > 0:
        curr_num_elems: int = math.ceil(rem_len / rem_num_arrays)
        arrays.append(array[curr_start_idx : (curr_start_idx + curr_num_elems)])
        curr_start_idx += curr_num_elems
        rem_len -= curr_num_elems
        rem_num_arrays -= 1
    return arrays
