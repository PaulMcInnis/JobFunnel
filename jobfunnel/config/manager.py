"""Config object to run JobFunnel
"""

import logging
import os
from typing import List, Optional

from jobfunnel.backend.scrapers.registry import SCRAPER_FROM_LOCALE
from jobfunnel.config.base import BaseConfig
from jobfunnel.config.delay import DelayConfig
from jobfunnel.config.proxy import ProxyConfig
from jobfunnel.config.search import SearchConfig
from jobfunnel.resources import BS4_PARSER

# pylint: disable=using-constant-test,unused-import
if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.backend.scrapers.base import BaseScraper
# pylint: enable=using-constant-test,unused-import


class JobFunnelConfigManager(BaseConfig):
    """Master config containing all the information we need to run jobfunnel"""

    def __init__(
        self,
        master_csv_file: str,
        user_block_list_file: str,
        duplicates_list_file: str,
        cache_folder: str,
        search_config: SearchConfig,
        log_file: str,
        log_level: Optional[int] = logging.INFO,
        no_scrape: Optional[bool] = False,
        bs4_parser: Optional[str] = BS4_PARSER,
        return_similar_results: Optional[bool] = False,
        delay_config: Optional[DelayConfig] = None,
        proxy_config: Optional[ProxyConfig] = None,
    ) -> None:
        """Init a config that determines how we will scrape jobs from Scrapers
        and how we will update CSV and filtering lists

        TODO: we might want to make a RunTimeConfig with the flags etc.

        Args:
            master_csv_file (str): path to the .csv file that user interacts w/
            user_block_list_file (str): path to a JSON that contains jobs user
                has decided to omit from their .csv file (i.e. archive status)
            duplicates_list_file (str): path to a JSON that contains jobs
                which TFIDF has identified to be duplicates of an existing job
            cache_folder (str): folder where all scrape data will be stored
            search_config (SearchConfig): SearchTerms config which contains the
                desired job search information (i.e. keywords)
            log_file (str): file to log all logger calls to
            log_level (int): level to log at, use 10 logging.DEBUG for more data
            no_scrape (Optional[bool], optional): If True, will not scrape data
                at all, instead will only update filters and CSV. Defaults to
                False.
            bs4_parser (Optional[str], optional): the parser to use for BS4.
            return_similar_resuts (Optional[bool], optional): If True, we will
                ask the job provider to provide more loosely-similar results for
                our search queries. NOTE: only a thing for indeed rn.
            delay_config (Optional[DelayConfig], optional): delay config object.
                Defaults to a default delay config object.
            proxy_config (Optional[ProxyConfig], optional): proxy config object.
                 Defaults to None, which will result in no proxy being used
        """
        super().__init__()
        self.master_csv_file = master_csv_file
        self.user_block_list_file = user_block_list_file
        self.duplicates_list_file = duplicates_list_file
        self.cache_folder = cache_folder
        self.search_config = search_config
        self.log_file = log_file
        self.log_level = log_level
        self.no_scrape = no_scrape
        self.bs4_parser = bs4_parser  # NOTE: this is not currently configurable
        self.return_similar_results = return_similar_results
        if not delay_config:
            # We will always use a delay config to be respectful
            self.delay_config = DelayConfig()
        else:
            self.delay_config = delay_config
        self.proxy_config = proxy_config

    @property
    def scrapers(self) -> List["BaseScraper"]:
        """All the compatible scrapers for the provider_name"""
        scrapers = []  # type: List[BaseScraper]
        for pr in self.search_config.providers:
            if pr in SCRAPER_FROM_LOCALE:
                scrapers.append(SCRAPER_FROM_LOCALE[pr][self.search_config.locale])
            else:
                raise ValueError(f"No scraper available for unknown provider {pr}")
        return scrapers

    @property
    def scraper_names(self) -> List[str]:
        """User-readable names of the scrapers we will be running"""
        return [s.__name__ for s in self.scrapers]

    def create_dirs(self) -> None:
        """Create the directories for attributes which refer to files / folders
        NOTE: should be called before we validate()
        """
        for file_path in [
            self.master_csv_file,
            self.user_block_list_file,
            self.duplicates_list_file,
            self.log_file,
        ]:
            output_dir = os.path.dirname(os.path.abspath(file_path))
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)

    def validate(self) -> None:
        """Validate the config object i.e. paths exit
        NOTE: will raise exceptions if issues are encountered.
        TODO: impl. more validation here
        """
        assert os.path.exists(self.cache_folder)
        self.search_config.validate()
        if self.proxy_config:
            self.proxy_config.validate()
        self.delay_config.validate()
