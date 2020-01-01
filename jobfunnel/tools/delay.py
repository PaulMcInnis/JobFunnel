"""
Module for calculating random or non-random delay
"""
from math import sqrt, log, ceil
from numpy import arange
from random import uniform
from scipy.special import expit
from typing import Dict, Union


def _h_delay(list_len: int, delay: Union[int, float]):
    """Sets single delay value to whole list"""
    delays = [delay] * list_len  # y = b where b = delay
    delays[0] = 0  # Set first element to zero to avoid first scrape delay
    return delays


def _lin_delay(list_len: int, delay: Union[int, float]):
    """
    Calculates y=.2*x and sets y=delay at point of intersection between lines
    """
    # Calculates x value where lines intersect
    its = 5 * delay  # its = intersection
    # Any delay of .2 or less is just hard delay
    if its <= 1:
        return _h_delay(list_len)
    else:
        # Prevents slicing from breaking if delay is a float
        if isinstance(its, float):
            its = int(ceil(its))
        # Create list of x values based on scrape list size
        delays = [*range(list_len)]
        delays[0:its] = [.2 * x for x in delays[0:its]]
        delays[its:] = [delay] * (len(delays) - its)
        return delays


# https://en.wikipedia.org/wiki/Generalised_logistic_function
def _rich_delay(list_len: int, delay: Union[int, float]):
    """ Calculates Richards/Sigmoid curve for delay"""
    if delay == 0:
        return _h_delay(list_len, 0)
    gr = sqrt(delay) * 4  # Growth rate
    y_0 = log(4 * delay)  # Y(0)
    # Calculates sigmoid curve using vars rewritten to be our x
    delays = delay * expit(arange(list_len) / gr - y_0)
    delays[0] = 0
    return delays.tolist()


def random_delay(list_len, delay_config: Dict):
    """Checks config parameters and returns calculated delay list"""
    if isinstance(list_len, list):
        list_len == len(list_len)
    try:
        # Init args
        delay = delay_config['delay']
        lb = 0

        # Check for set equation
        if delay_config['equation'] == 'hard':
            delays = _h_delay(list_len, delay)
        elif delay_config['equation'] == 'linear':
            delays = _lin_delay(list_len, delay)
        elif delay_config['equation'] == 'sigmoid':
            delays = _rich_delay(list_len, delay)

        # Check for lower bound value above zero
        if delay_config['lower_bound'] > 0:
            lb = delay_config['lower_bound']
            # Sets values list values greater than lb to lb
            for i, n in enumerate(delays):
                if n > lb:
                    break
                delays[i] = lb
        # Check if random delay was specified
        if delay_config['random']:
            delays = [round(uniform(lb, i), 3) for i in delays]
        else:
            delays = [round(i, 3) for i in delays]
        # Returns list of delay times
        return delays
    except (NameError, TypeError):
        raise ValueError("\n Somethings wrong with your delay config.")
