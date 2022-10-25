"""
This script recursively searches for MS images files in a given directory and stores them into a text file.
"""
import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Set

IMAGE_FILES_OUTPUT_FILE: str = "images.txt"


@dataclass()
class MicrosoftImageFile:
    """
    Depicts an .exe/.dll/.sym/.lib image file.
    """
    image_file: Path
    pdb_file: Optional[Path] = field(default=None)

    @classmethod
    def find_all_image_files_by_ext(cls, root_dir: Path, ext: str = "dll") -> List["MicrosoftImageFile"]:
        files: List[MicrosoftImageFile] = []
        for file in root_dir.rglob(f"*.{ext}"):
            base_file_name: str = str(file.name)[:-4]
            pdb_file: Path = file.parent / f"{base_file_name}.pdb"
            if pdb_file.exists():
                files.append(cls(image_file=file,
                                 pdb_file=pdb_file))
            else:
                files.append(cls(image_file=file))
        return files

    def __hash__(self) -> int:
        return hash(self.image_file.name)

    def __eq__(self, o: "MicrosoftImageFile") -> bool:
        return o.image_file.name == self.image_file.name


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
        "--ext",
        default="dll",
        choices=["dll", "exe", "sym", "lib"],
        help="Image file extension.",
    )
    parser.add_argument(
        "--image-filter",
        default=".*libmb2.*",
        help="Pattern to filter image names."
    )

    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_arguments()

    output_file: Path = Path(args.output_path) / IMAGE_FILES_OUTPUT_FILE
    root_dir: Path = Path(args.input_path).absolute()
    image_files: Set[MicrosoftImageFile] = set(MicrosoftImageFile.find_all_image_files_by_ext(
        root_dir=root_dir,
        ext=args.ext
    ))
    image_counter: int = 0
    with output_file.open("w+") as file:
        for image_file in image_files:
            image_name: str = image_file.image_file.name
            if re.match(args.image_filter, image_name, re.IGNORECASE):
                file.write(f"{image_file.image_file.name}\n")
                image_counter += 1

    print(f"Done writing image files, found {image_counter} images.")


if __name__ == '__main__':
    main()
