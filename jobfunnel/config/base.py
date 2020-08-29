"""Base config object with a validator
"""
from abc import ABC, abstractmethod


class BaseConfig(ABC):

    @abstractmethod
    def __init__(self) -> None:
        pass

    def validate(self) -> None:
        """This should raise Exceptions if self.attribs are bad
        NOTE: if we use sub-configs we could potentiall use Cerberus for this
        against any vars(Config)
        """
        pass
