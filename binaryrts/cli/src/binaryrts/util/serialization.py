import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, Type


class SerializerMixin(object):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def to_json(self: "SerializerMixin", filepath: Path) -> None:
        save_to_json(filepath=filepath, data=self.__dict__)

    @classmethod
    def from_json(cls: Type["SerializerMixin"], filepath: Path) -> "SerializerMixin":
        data: Dict = read_from_json(filepath=filepath)
        return cls(**data)

    def to_pickle(self, filepath: Path) -> None:
        save_to_pickle(filepath, self)

    @classmethod
    def from_pickle(cls, filepath: Path) -> "SerializerMixin":
        return read_from_pickle(filepath)


def save_to_json(filepath: Path, data: Any) -> None:
    with filepath.open("w+") as fp:
        json.dump(data, fp)


def read_from_json(filepath: Path) -> Dict:
    with filepath.open("r") as fp:
        data: Dict = json.load(fp)
    return data


def save_to_pickle(filepath: Path, data: Any) -> None:
    with filepath.open("wb+") as fp:
        pickle.dump(data, fp, pickle.HIGHEST_PROTOCOL)


def read_from_pickle(filepath: Path) -> Any:
    with filepath.open("rb") as fp:
        data = pickle.load(fp)
    return data
