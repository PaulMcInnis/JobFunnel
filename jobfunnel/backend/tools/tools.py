"""Assorted tools for all aspects of funnelin' that don't fit elsewhere
"""

from datetime import date, datetime, timedelta
import logging
import re
import sys
from typing import Optional

from dateutil.relativedelta import relativedelta
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager, IEDriverManager
from webdriver_manager.opera import OperaDriverManager

# Initialize list and store regex objects of date quantifiers
HOUR_REGEX = re.compile(r"(\d+)(?:[ +]{1,3})?(?:hour|hr|heure)")
DAY_REGEX = re.compile(r"(\d+)(?:[ +]{1,3})?(?:day|d|jour)")
MONTH_REGEX = re.compile(r"(\d+)(?:[ +]{1,3})?month|mois")
YEAR_REGEX = re.compile(r"(\d+)(?:[ +]{1,3})?year|annee")
RECENT_REGEX_A = re.compile(r"[tT]oday|[jJ]ust [pP]osted")
RECENT_REGEX_B = re.compile(r"[yY]esterday")


def get_logger(
    logger_name: str, level: int, file_path: str, message_format: str
) -> logging.Logger:
    """Initialize and return a logger
    NOTE: you can use this as a method to add logging to any function, but if
        you want to use this within a class, just inherit Logger class.
    TODO: make more easily configurable w/ defaults
    TODO: streamline
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    formatter = logging.Formatter(message_format)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    file_handler = logging.FileHandler(file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


class Logger:
    """Class that adds a self.logger attribute for stdio and fileio"""

    def __init__(
        self,
        level: int,
        file_path: Optional[str] = None,
        logger_name: Optional[str] = None,
        message_format: Optional[str] = None,
    ) -> None:
        """Add a logger to any class

        Args:
            level (int): logging level, which ought to be an Enum but isn't
            file_path (Optional[str], optional): file path to log messages to.
                NOTE: this logs at the specified log level.
            logger_name (Optional[str], optional): base name for the logger,
                should be unique. Defaults to inherited class name.
            message_format (Optional[str], optional): the formatting of the
                message to log. Defaults to a complete message with all info.
        """
        logger_name = logger_name or self.__class__.__name__
        message_format = message_format or (
            f"[%(asctime)s] [%(levelname)s] {logger_name}: %(message)s"
        )
        self.logger = get_logger(
            logger_name=logger_name,
            level=level,
            file_path=file_path,
            message_format=message_format,
        )


def calc_post_date_from_relative_str(date_str: str) -> date:
    """Identifies a job's post date via post age, updates in-place
    NOTE: we round to nearest day only so that comparisons dont capture
        portions of days.
    """
    post_date = datetime.now()  # type: date
    # Supports almost all formats like 7 hours|days and 7 hr|d|+d
    try:
        # Hours old
        hours_ago = HOUR_REGEX.findall(date_str)[0]
        post_date -= timedelta(hours=int(hours_ago))
    except IndexError:
        # Days old
        try:
            days_ago = DAY_REGEX.findall(date_str)[0]
            post_date -= timedelta(days=int(days_ago))
        except IndexError:
            # Months old
            try:
                months_ago = MONTH_REGEX.findall(date_str)[0]
                post_date -= relativedelta(months=int(months_ago))
            except IndexError:
                # Years old
                try:
                    years_ago = YEAR_REGEX.findall(date_str)[0]
                    post_date -= relativedelta(years=int(years_ago))
                except IndexError:
                    # Try phrases like 'today'/'just posted'/'yesterday'
                    if RECENT_REGEX_A.findall(date_str) and not post_date:
                        # Today
                        post_date = datetime.now()
                    elif RECENT_REGEX_B.findall(date_str):
                        # Yesterday
                        post_date -= timedelta(days=int(1))
                    elif not post_date:
                        # We have failed to correctly evaluate date.
                        raise ValueError(f"Unable to calculate date from:\n{date_str}")

    return post_date.replace(hour=0, minute=0, second=0, microsecond=0)


def get_webdriver():
    """Get whatever webdriver is availiable in the system.
    webdriver_manager and selenium are currently being used for this.
    Supported: Firefox, Chrome, Opera, Microsoft Edge, Internet Explorer
    Returns:
            webdriver that can be used for scraping.
            Returns None if we don't find a supported webdriver.
    """
    try:
        driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
    except Exception:
        try:
            driver = webdriver.Chrome(ChromeDriverManager().install())
        except Exception:
            try:
                driver = webdriver.Ie(IEDriverManager().install())
            except Exception:
                try:
                    driver = webdriver.Opera(
                        executable_path=OperaDriverManager().install()
                    )
                except Exception:
                    try:
                        driver = webdriver.Edge(EdgeChromiumDriverManager().install())
                    except Exception:
                        raise RuntimeError(
                            "Your browser is not supported. Must have one of "
                            "the following installed to scrape: [Firefox, "
                            "Chrome, Opera, Microsoft Edge, Internet Explorer]"
                        )
    return driver
