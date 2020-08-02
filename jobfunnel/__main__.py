#!python
"""Builds a config from CLI, runs desired scrapers and updates JSON + CSV

NOTE: you can test this from cloned source by running python -m jobfunnel
"""
import sys
from typing import Union

from .backend.jobfunnel import JobFunnel
from .config import JobFunnelConfig, SearchTerms
from .backend.scrapers import IndeedScraperCAEng


def main():
    """Parse CLI and call jobfunnel() to manage scrapers and lists
    """

    # Init TODO: parse CLI to do this.
    search_terms = SearchTerms(['Python', 'Scientist'], 'ON', None, 'waterloo', 25)
    config = JobFunnelConfig(
        't_m.csv', 't_udnl.json', 't_gdnl.json', './t_cache',
        search_terms, [IndeedScraperCAEng], 't_log.log'
    )
    JobFunnel(config).run()


if __name__ == '__main__':
    main()
