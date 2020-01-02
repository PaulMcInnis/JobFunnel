"""
Module for calculating random or non-random delay
"""
import sys

from math import ceil, log, sqrt
from numpy import arange
from random import uniform
from scipy.special import expit
from typing import Dict, Union
from logging import warning


def _c_delay(list_len: int, delay: Union[int, float]):
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
        return _c_delay(list_len, delay)
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
        # Init and check numerical arguments
        delay = delay_config['delay']
        if delay <= 0:
            raise ValueError("\nYour delay is set to 0 or less.\nIf you want "
                             "to turn off delaying use the --no_delay flag in "
                             "the command line or set \'set_delay\' to False "
                             "in your settings file.\nCancelling execution...")
            sys.exit(1)

        min_delay = delay_config['min_delay']
        if min_delay < 0 or min_delay > delay:
            warning("\nMinimum delay is set below 0, or higher than delay."
                    "\nSetting to 0 and continuing execution."
                    "\nIf this was a mistake, check your command line"
                    " arguments or settings file. \n")
            min_delay = 0

        # Delay calculations using specified equations
        if delay_config['function'] == 'constant':
            delay_calcs = _c_delay(list_len, delay)
        elif delay_config['function'] == 'linear':
            delay_calcs = _lin_delay(list_len, delay)
        elif delay_config['function'] == 'sigmoid':
            delay_calcs = _rich_delay(list_len, delay)

        # Check if minimum delay is above 0 and less than last element
        if 0 < min_delay < delay_calcs[-1]:
            # Sets min_delay to values greater than itself in delay_calcs
            for i, n in enumerate(delay_calcs):
                if n > min_delay:
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
                delays = [round(uniform(min_delay, x), 3) for x in delay_calcs]

        else:
            delays = [round(i, 3) for i in delay_calcs]
        # Always set the first element to 0
        delays[0] = 0
        return delays

    # Captures possible errors and raise error about delay config
    except (NameError, TypeError):
        raise ValueError("\nSomethings wrong, check your command line argument"
                         "s or delay config located in you settings file.")
