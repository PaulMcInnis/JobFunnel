"""Assorted tools for all aspects of funnelin' that don't fit elsewhere
"""
import re
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import IEDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.opera import OperaDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver


# Initialize list and store regex objects of date quantifiers
HOUR_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?(?:hour|hr)')
DAY_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?(?:day|d)')
MONTH_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?month')
YEAR_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?year')
RECENT_REGEX_A = re.compile(r'[tT]oday|[jJ]ust [pP]osted')
RECENT_REGEX_B = re.compile(r'[yY]esterday')


def calc_post_date_from_relative_str(date_str: str) -> date:
    """Identifies a job's post date via post age, updates in-place
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
                        raise ValueError(
                            f"Unable to calculate date from:\n{date_str}"
                        )
    return post_date

def get_webdriver():
    """Get whatever webdriver is availiable in the system.
    webdriver_manager and selenium are currently being used for this.
    Supported: Firefox, Chrome, Opera, Microsoft Edge, Internet Explorer
    Returns:
            webdriver that can be used for scraping.
            Returns None if we don't find a supported webdriver.
    """
    try:
        driver = webdriver.Firefox(
            executable_path=GeckoDriverManager().install()
        )
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
                        driver = webdriver.Edge(
                            EdgeChromiumDriverManager().install()
                        )
                    except Exception:
                        raise RuntimeError(
                            "Your browser is not supported. Must have one of "
                            "the following installed to scrape: [Firefox, "
                            "Chrome, Opera, Microsoft Edge, Internet Explorer]"
                        )
    return driver


def split_url(url):
    # capture protocol, ip address and port from given url
    match = re.match(r'^(http[s]?):\/\/([A-Za-z0-9.]+):([0-9]+)?(.*)$', url)

    # if not all groups have a match, match will be None
    if match is not None:
        return {
            'protocol': match.group(1),
            'ip_address': match.group(2),
            'port': match.group(3),
        }
    else:
        return None
