"""Config object to run JobFunnel
"""
import logging
from typing import Optional, List, Dict, Any
import os

from jobfunnel.backend.scrapers import (
    BaseScraper, IndeedScraperCAEng, IndeedScraperUSAEng)
from jobfunnel.config import BaseConfig, ProxyConfig, SearchConfig, DelayConfig


SCRAPER_MAP = {
    'indeed': IndeedScraperCAEng,  # TODO: deprecate and enforce below options
    'INDEED_CANADA_ENG': IndeedScraperCAEng,
    'INDEED_USA_ENG': IndeedScraperUSAEng,
    #'monster': MonsterScraperCAEng,  FIXME
    #'MONSTER_CANADA_ENG': MonsterScraperCAEng,
}


class JobFunnelConfig(BaseConfig):
    """Master config containing all the information we need to run jobfunnel
    """

    def __init__(self,
                 master_csv_file: str,
                 user_block_list_file: str,
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

        # Create folder that out output files are within, if it doesn't exist
        for path_attr in [self.master_csv_file, self.user_block_list_file,
                          self.cache_folder]:
            if path_attr:
                output_dir = os.path.dirname(os.path.abspath(path_attr))
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

        self.validate()

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


def build_funnel_cfg_from_legacy(config: Dict[str, Any]):
    """Build config objects from legacy config dict
    FIXME: when we implement a yaml parser with localization we can have it
    """
    search_cfg = SearchConfig(
        keywords=config['search_terms']['keywords'],
        province=config['search_terms']['region']['province'],
        state=None,
        city=config['search_terms']['region']['city'],
        distance_radius_km=config['search_terms']['region']['radius'],
        return_similar_results=False,
        max_listing_days=config['max_listing_days'],
        blocked_company_names=config['black_list'],
    )

    delay_cfg = DelayConfig(
        duration=config['delay_config']['delay'],
        min_delay=config['delay_config']['min_delay'],
        function_name=config['delay_config']['function'],
        random=config['delay_config']['random'],
        converge=config['delay_config']['converge'],
    )

    if config['proxy']:
        proxy_cfg = ProxyConfig(
            protocol=config['proxy']['protocol'],
            ip_address=config['proxy']['ip_address'],
            port=config['proxy']['port'],
        )
    else:
        proxy_cfg = None

    funnel_cfg = JobFunnelConfig(
        master_csv_file=config['master_list_path'],
        user_block_list_file=config['filter_list_path'],
        cache_folder=config['data_path'],
        search_terms=search_cfg,
        scrapers=[SCRAPER_MAP[sc_name] for sc_name in config['providers']],
        log_file=config['log_path'],
        log_level=config['log_level'],
        no_scrape=config['no_scrape'],
        delay_config=delay_cfg,
        proxy_config=proxy_cfg,
    )
    return funnel_cfg
