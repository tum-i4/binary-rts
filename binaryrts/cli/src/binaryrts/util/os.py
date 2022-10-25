import platform
from enum import Enum


class OSPlatform(Enum):
    """
    OS names as returned by platform.system
    """

    DARWIN = "Darwin"
    WINDOWS = "Windows"
    LINUX = "Linux"

    @classmethod
    def has_value(cls, value: str) -> bool:
        return value in cls._value2member_map_

    @classmethod
    def get_os(cls, value: str) -> "OSPlatform":
        if not cls.has_value(value):
            raise Exception(f"Unsupported OS {value}.")
        return cls._value2member_map_[value]


def get_platform_name() -> str:
    """
    Return the operating system's name.
    :return: The OS name
    """
    return platform.system()


def get_os() -> OSPlatform:
    """
    Return the operating system's name.
    :return: The OS name
    """
    return OSPlatform.get_os(get_platform_name())


def os_is_windows() -> bool:
    """
    Check if OS is windows.
    :return: True if OS is windows.
    """
    return get_os() == OSPlatform.WINDOWS
