"""
This script recursively searches for MS images files in a given directory, extracts source line information,
and stores the list into a file.
"""
import argparse
import multiprocessing as mp
import os
import re
import subprocess as sb
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Set, Callable, Iterable, Tuple

SYMBOLS_FILE_EXT: str = ".binaryrts"


@dataclass
class MicrosoftImageFile:
    """
    Depicts an MS image file.
    """

    image_file: Path
    pdb_file: Optional[Path] = field(default=None)

    @classmethod
    def find_all_image_files_by_ext(
            cls, root_dir: Path, ext: str = "dll", regex: str = ".*"
    ) -> List["MicrosoftImageFile"]:
        files: List[MicrosoftImageFile] = []
        for file in root_dir.rglob(f"*.{ext}"):
            if not re.match(regex, file.name, re.IGNORECASE):
                continue
            pdb_files = list(file.parent.glob("*.pdb"))
            # we only consider image files with .pdb here
            if len(pdb_files) > 0:
                pdb_files.sort(key=lambda f: f.stat().st_size, reverse=True)
                pdb_file: Path = file.parent / pdb_files[0].name
                files.append(cls(image_file=file, pdb_file=pdb_file))
        files.sort(key=lambda f: f.pdb_file.stat().st_size, reverse=True)
        return files

    def __hash__(self) -> int:
        return hash(self.image_file.name)

    def __eq__(self, o: "MicrosoftImageFile") -> bool:
        return o.image_file.name == self.image_file.name


def run_with_multi_processing(func: Callable, arguments: Iterable, n_cpu: int):
    """
    Run a function for each element in arguments with multiprocessing.
    """
    with ThreadPoolExecutor(max_workers=n_cpu) as executor:
        for args in arguments:
            executor.submit(func, *args)


def call_extractor(executable: Path, input_file: Path, sources_regex: str):
    command: str = " ".join(
        [
            f'"{executable.__str__()}"',  # quotes to support whitespaces in path
            f'-input "{input_file.__str__()}"',
            f'-regex "{sources_regex}"',
            # FIXME: maybe this could be changed to '-mode symbols' in the future,
            #  but debug symbols are unreliable at the moment
            f"-mode lines",
        ]
    )
    process: sb.CompletedProcess = sb.run(
        command,
        text=True,
        capture_output=True,
    )
    print(
        f"Exit code: {process.returncode}\nstdout: {process.stdout}\nstderr: {process.stderr}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-path",
        "-i",
        default=os.getcwd(),
        help=f"Root directory from where to search for image files.",
    )
    parser.add_argument(
        "--extractor",
        required=True,
        help="Path to binary_rts_extractor executable.",
    )
    parser.add_argument(
        "--ext",
        default="dll",
        choices=["dll", "exe"],
        help="Image file extension.",
    )
    parser.add_argument(
        "--cpus",
        default=mp.cpu_count(),
        type=int,
        help="Process count for parallelization.",
    )
    parser.add_argument(
        "--image-filter", default=".*", help="Pattern to filter image names."
    )
    parser.add_argument(
        "--sources",
        default=".*mb2cpp(?!.external).*",
        help="Pattern to filter for source files.",
    )
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_arguments()
    root_dir: Path = Path(args.input_path).absolute()
    extractor: Path = Path(args.extractor).absolute()
    image_files: Set[MicrosoftImageFile] = set(
        MicrosoftImageFile.find_all_image_files_by_ext(root_dir=root_dir, ext=args.ext, regex=args.image_filter)
    )
    mp_args: List[Tuple[Path, Path, str]] = [
        (extractor, file.image_file, args.sources) for file in image_files
    ]
    run_with_multi_processing(
        func=call_extractor,
        arguments=mp_args,
        n_cpu=args.cpus,
    )


if __name__ == "__main__":
    main()
