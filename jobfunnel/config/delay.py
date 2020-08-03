"""Simple config object to contain the delay configuration
"""
from jobfunnel.config.base import BaseConfig


class DelayConfig(BaseConfig):
    """Simple config object to contain the delay configuration
    """
    def __init__(self, duration: float, min_delay: float, function_name: str,
                 random: bool = False, converge: bool = False):
        # TODO: document
        self.duration = duration
        self.min_delay = min_delay
        self.function_name = function_name
        self.random = random
        self.converge = converge

    def validate(self) -> None:
        assert self.function_name in ['constant', 'linear', 'sigmoid']

        if self.duration <= 0:
            raise ValueError("Your delay duration is set to 0 or less.")

        if self.min_delay < 0 or self.min_delay >= self.duration:
            raise ValueError(
                "Minimum delay is below 0, or more than or equal to delay."
            )

