"""Assorted tools for all aspects of funnelin' that don't fit elsewhere
"""
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import IEDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.opera import OperaDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver


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
