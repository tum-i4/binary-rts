from abc import ABC, abstractmethod
from enum import Enum


class CoverageFormat(str, Enum):
    LCOV = "LCOV"
    SONAR = "SONAR"


class CoverageConverter(ABC):

    OUTPUT_FILE: str

    @abstractmethod
    def convert(self) -> str:
        """
        Converts the coverage into a coverage format.

        @return: Converted coverage as string
        """
        pass
