"""
Module containing base interfaces for SCM systems.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List


class ChangelistItemAction(Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


@dataclass(unsafe_hash=True)
class ChangelistItem(object):
    filepath: Path
    action: ChangelistItemAction


@dataclass()
class Changelist:
    """
    Changelists are composites of change list items.
    They can comprise ChangelistItems from multiple commits or a single commit.
    Commits contain only one changelist.
    """

    items: List[ChangelistItem] = field(default_factory=list)

    def __eq__(self, other: "Changelist"):
        return set(self.items) == set(other.items)
