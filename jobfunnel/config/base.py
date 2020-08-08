"""Base config object with a validator
"""
from abc import ABC, abstractmethod


class BaseConfig(ABC):

    @abstractmethod
    def __init__(self) -> None:
        pass

    def validate(self) -> None:
        """This should raise Exceptions if self.attribs are bad
        FIXME: move this into cerberus schema validation, or, use the same
        validators it does here.
        """
        pass
