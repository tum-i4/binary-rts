"""
This script recursively searches for MS images files in a given directory, extracts functions, and stores the list into a file.
"""
import argparse
import multiprocessing as mp
import os
import re
import subprocess as sb
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Set, Callable, Iterable, Tuple

IMAGE_FILES_OUTPUT_FILE: str = "images.txt"
FUNCTIONS_FILE_EXT: str = ".functions"

@dataclass()
class MicrosoftImageFile:
    """
    Depicts an MS image file.
    """
    image_file: Path
    pdb_file: Optional[Path] = field(default=None)

    @classmethod
    def find_all_image_files_by_ext(cls, root_dir: Path, ext: str = "dll") -> List["MicrosoftImageFile"]:
        files: List[MicrosoftImageFile] = []
        for file in root_dir.rglob(f"*.{ext}"):
            pdb_files = list(file.parent.glob("*.pdb"))
            # we only consider image files with .pdb here
            if len(pdb_files) > 0:
                pdb_file: Path = file.parent / pdb_files[0].name
                files.append(cls(image_file=file,
                                 pdb_file=pdb_file))
        return files

    def __hash__(self) -> int:
        return hash(self.image_file.name)

    def __eq__(self, o: "MicrosoftImageFile") -> bool:
        return o.image_file.name == self.image_file.name


def run_with_multi_processing(func: Callable, iterable: Iterable, n_cpu: int) -> List:
    """
    Run a function for each element in an iterable with multi-processing.

    :param func:
    :param iterable:
    :param n_cpu:
    :return:
    """
    print(f"Starting multi-processing with {n_cpu} CPUs.")
    with mp.Pool(processes=n_cpu) as pool:
        try:
            results: List = pool.starmap(func, iterable)
        except TypeError as e:
            try:
                results: List = pool.map(func, iterable)
            except TypeError as e:
                raise Exception("Failed to run function in parallel.")
    return results


def call_extractor(executable: Path, input_file: Path, sources_regex: str):
    command: str = " ".join(
        [
            executable.__str__(),
            f"-input {input_file.__str__()}",
            f"-sources {sources_regex}",
        ]
    )
    process: sb.CompletedProcess = sb.run(
        command,
        text=True,
        capture_output=True,
    )
    output: str = process.stdout + process.stderr
    print(f"Exit code: {process.returncode} Output: {output}")


def parse_arguments() -> argparse.Namespace:
    """
    Define and parse program arguments.

    :return: arguments captured in object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-path",
        "-i",
        default=os.getcwd(),
        help=f"Root directory from where to search for image files.",
    )
    parser.add_argument(
        "--output-path",
        "-o",
        default=os.getcwd(),
        help="Output path where to save images file.",
    )
    parser.add_argument(
        "--extractor",
        required=True,
        help="Path to binary_rts_extractor.exe.",
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
        "--image-filter",
        default=".*",
        help="Pattern to filter image names."
    )
    parser.add_argument(
        "--sources",
        default=".*mb2cpp.*",
        help="Pattern to filter for source files."
    )
    parser.add_argument(
        "--cache",
        default=False,
        action="store_true",
        help="Whether to use existing extracted functions files.",
    )
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_arguments()
    output_file: Path = Path(args.output_path) / IMAGE_FILES_OUTPUT_FILE
    root_dir: Path = Path(args.input_path).absolute()
    extractor: Path = Path(args.extractor).absolute()
    image_files: Set[MicrosoftImageFile] = set(MicrosoftImageFile.find_all_image_files_by_ext(
        root_dir=root_dir,
        ext=args.ext
    ))
    image_counter: int = 0
    mp_iterable: List[Tuple[Path, Path, str]] = [
        (extractor, file.image_file, args.sources)
        for file in image_files
        if not args.cache or not (file.image_file.parent / f"{file.image_file.name}{FUNCTIONS_FILE_EXT}").exists()
    ]
    run_with_multi_processing(
        func=call_extractor,
        iterable=mp_iterable,
        n_cpu=args.cpus,
    )
    with output_file.open("w+") as file:
        for image_file in image_files:
            image_name: str = image_file.image_file.name
            if re.match(args.image_filter, image_name, re.IGNORECASE):
                file.write(f"{image_file.image_file.__str__()}\n")
                image_counter += 1

    print(f"Done writing image files, found {image_counter} images.")


if __name__ == '__main__':
    main()
