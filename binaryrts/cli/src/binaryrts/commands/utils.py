import os
from pathlib import Path
from typing import List, Set

import typer

from binaryrts.commands.select import EXCLUDED_TESTS_FILE

app = typer.Typer()


@app.callback()
def utils():
    """
    BinaryRTS utilities
    """
    pass


@app.command()
def merge(
        output: Path = typer.Option(
            lambda: Path(os.getcwd()),
            "-o",
            writable=True,
            exists=False,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
        include_files: List[Path] = typer.Option(
            [],
            "--include",
            help="A list of `included.txt` files that ought to be merged.",
        ),
        exclude_files: List[Path] = typer.Option(
            [],
            "--exclude",
            help="A list of `excluded.txt` files that ought to be merged.",
        ),
):
    """
    Merges includes and excludes files into a single excludes file that can be used for RTS.
    """
    final_excludes: Set[str] = set()
    for file in exclude_files:
        with file.open("r") as fp:
            for line in fp:
                test_id: str = line.strip()
                if len(test_id) > 0:
                    final_excludes.add(test_id)
    for file in include_files:
        with file.open("r") as fp:
            for line in fp:
                test_id: str = line.strip()
                if test_id == "*":
                    final_excludes = set()
                    break
                if len(test_id) > 0 and test_id in final_excludes:
                    final_excludes.remove(test_id)
    output.mkdir(parents=True, exist_ok=True)
    (output / EXCLUDED_TESTS_FILE).write_text("\n".join(final_excludes))
