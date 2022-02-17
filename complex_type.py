import os
import abc
from typing import Dict

from symdump.object_file import ObjectFile


class ComplexType(abc.ABC):
    def __init__(self, name: str, is_fake: bool):
        self._name = name
        self._is_fake = is_fake

    @property
    def name(self):
        return self._name

    @property
    def is_fake(self):
        return self._is_fake

    @abc.abstractmethod
    def dump(self) -> None: pass

    @abc.abstractmethod
    def resolve_typedefs(self, object_file: ObjectFile) -> None: pass
