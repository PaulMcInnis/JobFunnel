"""Base config object with a validator
"""
from abc import ABC, abstractmethod


class BaseConfig(ABC):

    @abstractmethod
    def __init__(self) -> None:
        pass

    def validate(self) -> None:
        """This should raise Exceptions if self.attribs are bad
        FIXME: some way to run this on object creation would be nice
        """
        pass
