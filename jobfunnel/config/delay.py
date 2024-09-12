"""Simple config object to contain the delay configuration
"""

from jobfunnel.config.base import BaseConfig
from jobfunnel.resources import DelayAlgorithm
from jobfunnel.resources.defaults import (
    DEFAULT_DELAY_ALGORITHM,
    DEFAULT_DELAY_MAX_DURATION,
    DEFAULT_DELAY_MIN_DURATION,
    DEFAULT_RANDOM_CONVERGING_DELAY,
    DEFAULT_RANDOM_DELAY,
)


class DelayConfig(BaseConfig):
    """Simple config object to contain the delay configuration"""

    def __init__(
        self,
        max_duration: float = DEFAULT_DELAY_MAX_DURATION,
        min_duration: float = DEFAULT_DELAY_MIN_DURATION,
        algorithm: DelayAlgorithm = DEFAULT_DELAY_ALGORITHM,
        random: bool = DEFAULT_RANDOM_DELAY,
        converge: bool = DEFAULT_RANDOM_CONVERGING_DELAY,
    ):
        """Delaying Configuration for GET requests

        Args:
            max_duration (float, optional): max duration.
                Defaults to DEFAULT_DELAY_MAX_DURATION.
            min_duration (float, optional): min duration.
                Defaults to DEFAULT_DELAY_MIN_DURATION.
            algorithm (DelayAlgorithm, optional): algorithm.
                Defaults to DEFAULT_DELAY_ALGORITHM.
            random (bool, optional): [enable random delaying.
                Defaults to DEFAULT_RANDOM_DELAY.
            converge (bool, optional): enable random converging delaying.
                Defaults to DEFAULT_RANDOM_CONVERGING_DELAY.
        """
        super().__init__()
        self.max_duration = max_duration
        self.min_duration = min_duration
        self.algorithm = algorithm
        self.random = random
        self.converge = converge

    def validate(self) -> None:
        if self.max_duration <= 0:
            raise ValueError("Your max delay is set to 0 or less.")
        if self.min_duration <= 0 or self.min_duration >= self.max_duration:
            raise ValueError(
                "Minimum delay is below 0, or more than or equal to delay."
            )
        if type(self.algorithm) != DelayAlgorithm:
            raise ValueError(f"Invalid Value for delaying algorithm: {self.algorithm}")
        if self.converge and not self.random:
            raise ValueError(
                "You cannot configure convering random delay without also "
                "enabling random delaying"
            )
