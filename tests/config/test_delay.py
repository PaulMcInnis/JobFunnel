"""Test the DelayConfig
"""

import pytest

from jobfunnel.config import DelayConfig
from jobfunnel.resources import DelayAlgorithm


@pytest.mark.parametrize(
    "max_duration, min_duration, invalid_dur",
    [
        (1.0, 1.0, True),
        (-1.0, 1.0, True),
        (5.0, 0.0, True),
        (5.0, 1.0, False),
    ],
)
@pytest.mark.parametrize(
    "random, converge, invalid_rand",
    [
        (True, True, False),
        (True, False, False),
        (False, True, True),
    ],
)
@pytest.mark.parametrize("delay_algorithm", (DelayAlgorithm.LINEAR, None))
def test_delay_config_validate(
    max_duration,
    min_duration,
    invalid_dur,
    delay_algorithm,
    random,
    converge,
    invalid_rand,
):
    """Test DelayConfig
    TODO: test messages too
    """
    cfg = DelayConfig(
        max_duration=max_duration,
        min_duration=min_duration,
        algorithm=delay_algorithm,
        random=random,
        converge=converge,
    )

    # FUT
    if invalid_dur or not delay_algorithm or invalid_rand:
        with pytest.raises(ValueError):
            cfg.validate()
    else:
        cfg.validate()
