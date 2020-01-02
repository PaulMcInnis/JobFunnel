"""
Module for calculating random or non-random delay
"""
from math import ceil, log, sqrt
from numpy import arange, linspace
from random import uniform
from scipy.special import expit
from typing import Dict, Union


def _h_delay(list_len: int, delay: Union[int, float]):
    """Sets single delay value to whole list"""
    delays = [delay] * list_len  # y = b where b = delay
    delays[0] = 0  # Set first element to zero to avoid first scrape delay

    # Sets a small offset to hard delay, so scrapes don't start at same time
    offset = .2
    increment = .2
    # Checks if delay is less than 1.5 to prevent negative or zero values
    if delay < 1.5:
        offset = delay/8
        increment = delay/8
    for i in reversed(range(1, 8)):
        # Exception catching if list length is less than 8
        try:
            delays[i] -= offset
            offset += increment
        except IndexError:
            pass
    return delays


def _lin_delay(list_len: int, delay: Union[int, float]):
    """Calculates y=.2*x and sets y=delay at intersection of x between lines"""
    # Calculates x value where lines intersect
    its = 5 * delay  # its = intersection
    # Any delay of .2 or less is hard delay
    if its <= 1:
        return _h_delay(list_len, delay)
    else:
        # Prevents slicing from breaking if delay is a float
        if isinstance(its, float):
            its = int(ceil(its))
        # Create list of x values based on scrape list size
        delays = [*range(list_len)]
        delays[0:its] = [.2*x for x in delays[0:its]]
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


def delay_alg(list_len, delay_config: Dict):
    """ Checks delay config and returns calculated delay list

        Args:
            list_len: length of scrape job list
            delay_config: Delay configuration dictionary

        Returns:
            list of delay time matching length of scrape job list
    """
    if isinstance(list_len, list):  # Prevents breaking if a list was passed
        list_len == len(list_len)
    try:
        # Init args
        delay = delay_config['delay']
        lb = delay_config['lower_bound']

        # Delay calculations using specified equations
        if delay_config['equation'] == 'hard':
            delay_calcs = _h_delay(list_len, delay)
        elif delay_config['equation'] == 'linear':
            delay_calcs = _lin_delay(list_len, delay)
        elif delay_config['equation'] == 'sigmoid':
            delay_calcs = _rich_delay(list_len, delay)

        # Check if lower bound is above 0 and less than last element
        if 0 < lb < delay_calcs[-1]:
            # Sets lb to values greater than itself to delay_calcs
            for i, n in enumerate(delay_calcs):
                if n > lb:
                    break
                delay_calcs[i] = lb

        # Outputs final list of delays rounded up to 3 decimal places
        if delay_config['random']:  # Check if random delay was specified
            # random.uniform(a, b) a = lower bound, b = upper bound
            if delay_config['converge']:  # Checks if converging delay is True
                # delay_calcs = lower bound, delay = upper bound
                delays = [round(uniform(x, delay), 3) for x in delay_calcs]
            else:
                # lb = lower bounds, delay_calcs = upper bound
                delays = [round(uniform(lb, x), 3) for x in delay_calcs]

        else:
            delays = [round(i, 3) for i in delay_calcs]
        # Always set the first element to 0
        delays[0] = 0
        return delays

    # Captures possible errors and raise error about delay config
    except (NameError, TypeError):
        raise ValueError("\n Somethings wrong with your delay config.")
