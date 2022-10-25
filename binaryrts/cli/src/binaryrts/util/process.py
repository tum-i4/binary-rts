import os
from pathlib import Path
from typing import Optional

from binaryrts.util.os import os_is_windows

MS_EXE_FILE_SUFFIX: str = ".exe"


def is_executable_program(filepath: Path) -> bool:
    """
    Returns True if the given filepath is an executable program.

    :param filepath:
    :return:
    """
    # An .exe file cannot be executed on non-Windows systems.
    if not os_is_windows() and MS_EXE_FILE_SUFFIX in filepath.name:
        return False

    return filepath.is_file() and os.access(filepath, os.X_OK)


def check_executable_exists(program: str) -> Optional[str]:
    """
    Check if provided program is an executable program, if yes, return executable file name or path it.

    :param program: Name of executable program (can be in short form)
    :return: executable file name (if in PATH) or path to executable
    """
    executable: Optional[str] = None

    filepath, filename = os.path.split(program)
    if filepath:
        if is_executable_program(Path(program)) or is_executable_program(
            Path(program + MS_EXE_FILE_SUFFIX)
        ):
            executable = program
    if not executable:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file: str = os.path.join(path, filename)
            if is_executable_program(Path(exe_file)) or is_executable_program(
                Path(exe_file + MS_EXE_FILE_SUFFIX)
            ):
                executable = exe_file
    return executable
