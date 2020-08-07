"""Simple config object to contain the delay configuration
"""
from jobfunnel.config.base import BaseConfig
from jobfunnel.resources import DelayAlgorithm


class DelayConfig(BaseConfig):
    """Simple config object to contain the delay configuration
    """
    def __init__(self, duration: float, min_delay: float,
                 algorithm: DelayAlgorithm, random: bool = False,
                 converge: bool = False):
        # TODO: document
        self.duration = duration
        self.min_delay = min_delay
        self.algorithm = algorithm
        self.random = random
        self.converge = converge

    def validate(self) -> None:
        if self.duration <= 0:
            raise ValueError("Your delay duration is set to 0 or less.")

        if self.min_delay < 0 or self.min_delay >= self.duration:
            raise ValueError(
                "Minimum delay is below 0, or more than or equal to delay."
            )
