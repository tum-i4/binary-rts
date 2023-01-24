from operator import itemgetter
from pathlib import Path
from typing import List, Tuple


def slice_file_into_chunks(file: Path, line_ranges: List[Tuple[int, int]]) -> List[str]:
    ranges: List[range] = [range(min(r), max(r) + 1) for r in line_ranges]
    chunks: List[str] = ["" for _ in ranges]
    with file.open(mode="r", encoding="utf-8") as fp:
        max_line_no: int = max([(min(r), max(r)) for r in line_ranges], key=itemgetter(1))[1]
        for line_no, line in enumerate(fp):
            for chunk_idx, line_range in enumerate(ranges):
                if (line_no + 1) in line_range:
                    chunks[chunk_idx] += line
            if (line_no + 1) == max_line_no:
                break
    return chunks
