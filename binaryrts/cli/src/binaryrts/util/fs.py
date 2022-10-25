import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, AnyStr, Generator, Iterable, List


def delete_files(paths: Iterable[Path]) -> None:
    for file in paths:
        try:
            file.unlink()
        except Exception as e:
            logging.warning(f"{e}: Failed to delete file: {file}")


def get_parent(path: Path, depth: int = 1) -> Path:
    """
    Returns the n-th parent of a path.
    """
    if depth == 0:
        return path
    depth -= 1
    return get_parent(path.parent, depth)


@contextmanager
def temp_file(suffix: Optional[str] = None) -> Generator[Path, None, None]:
    """
    Create temporary file and yield path.
    """
    with temp_path(change_dir=False) as temp_dir:
        file_path = (Path(temp_dir) / f"file{suffix or '.tmp'}").absolute()
        file_path.touch()
        yield file_path


@contextmanager
def temp_path(change_dir: bool = True):
    """
    Create temporary directory, navigate into it and yield path to it.
    On deletion of context (i.e. `with` clause), navigate back to original path and remove temporary directory.
    """
    original_wd: str = os.getcwd()

    tmp_path: Optional[AnyStr] = None
    try:
        tmp_path = tempfile.mkdtemp()
        if change_dir:
            os.chdir(tmp_path)

        yield tmp_path
    finally:
        if change_dir:
            os.chdir(original_wd)

        if tmp_path is not None and os.path.exists(tmp_path) is True:
            try:
                shutil.rmtree(tmp_path)
            except Exception as e:
                logging.debug(
                    "Exception occurred when removing temporary path {}.".format(
                        tmp_path
                    )
                )
                logging.debug(e)
                pass


def is_relative_to(path: Path, other_path: Path) -> bool:
    """
    Return True if the first path is relative to the other path.
    """
    try:
        path.relative_to(other_path)
        return True
    except ValueError:
        return False


def has_ext(file: Path, exts: List[str]) -> bool:
    return os.path.splitext(file.name)[-1].lower() in exts
