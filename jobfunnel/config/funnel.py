"""Config object to run JobFunnel
"""
import logging
from typing import Optional, List
import os

from jobfunnel.backend.scrapers import BaseScraper
from jobfunnel.config import BaseConfig, ProxyConfig, SearchConfig, DelayConfig


class JobFunnelConfig(BaseConfig):
    """Master config containing all the information we need to run jobfunnel
    """

    def __init__(self,
                 master_csv_file: str,
                 user_block_list_file: str,
                 company_block_list_file: str,
                 cache_folder: str,
                 search_terms: SearchConfig,
                 scrapers: List[BaseScraper],
                 log_file: str,
                 log_level: Optional[int] = logging.INFO,
                 no_scrape: Optional[bool] = False,
                 delay_config: Optional[DelayConfig] = None,
                 proxy_config: Optional[ProxyConfig] = None) -> None:
        """Init a config that determines how we will scrape jobs from Scrapers
        and how we will update CSV and filtering lists

        Args:
            master_csv_file (str): path to the .csv file that user interacts w/
            user_block_list_file (str): path to a JSON that contains jobs user
                has decided to omit from their .csv file (i.e. archive status)
            company_block_list_file (str): path to a JSON containing companies
                that the user wants to never see in their .csv file for all
                their searches
            cache_folder (str): folder where all scrape data will be stored
            search_terms (SearchTerms): SearchTerms config which contains the
                desired job search information (i.e. keywords)
            scrapers (List[BaseScraper]): List of scrapers we will scrape from
            log_file (str): file to log all logger calls to
            log_level (int): level to log at, use 10 logging.DEBUG for more data
            no_scrape (Optional[bool], optional): If True, will not scrape data
                at all, instead will only update filters and CSV. Defaults to
                False.
            delay_config (Optional[DelayConfig], optional): delay config object.
                Defaults to a default delay config object.
            proxy_config (Optional[ProxyConfig], optional): proxy config object.
                 Defaults to None, which will result in no proxy being used
        """
        self.master_csv_file = master_csv_file
        self.user_block_list_file = user_block_list_file
        self.company_block_list_file = company_block_list_file
        self.cache_folder = cache_folder
        self.search_terms = search_terms
        self.scrapers = scrapers
        self.log_file = log_file
        self.log_level = log_level
        self.no_scrape = no_scrape
        if not delay_config:
            self.delay_config = DelayConfig(5.0, 1.0, 'linear')
        else:
            self.delay_config = delay_config
        self.proxy_config = proxy_config

    @property
    def scraper_names(self) -> str:
        """User-readable names of the scrapers we will be running
        """
        return [s.__name__ for s in self.scrapers]

    def create_dirs(self) -> None:
        """Create any missing dirs
        """
        if not os.path.exists(self.cache_folder):  # TODO: put this in tmpdir?
            os.makedirs(self.cache_folder)

    def validate(self) -> None:
        """Validate the config object i.e. paths exit
        NOTE: will raise exceptions if issues are encountered.
        FIXME: impl. more validation here
        """
        assert os.path.exists(self.cache_folder)
        self.search_terms.validate()
        if self.proxy_config:
            self.proxy_config.validate()
        self.delay_config.validate()
