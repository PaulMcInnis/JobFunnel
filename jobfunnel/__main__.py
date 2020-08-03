#!python
"""Builds a config from CLI, runs desired scrapers and updates JSON + CSV

NOTE: you can test this from cloned source by running python -m jobfunnel

TODO/FIXME:
    * make it easier to continue an existing search
    * make it easier to run multiple searches at once w.r.t caching
    * simplified CLI args with new --recover and --clean options
    * impl Cereberus for YAML validation
    * add warning around seperate cache folders blocklists per search
    * document API usage in readme
    ** add back the duplicates JSON
"""
import sys
from typing import Union
import logging

from .backend.jobfunnel import JobFunnel
from .config import JobFunnelConfig, SearchConfig
from .backend.scrapers import IndeedScraperCAEng


def main():
    """Parse CLI and call jobfunnel() to manage scrapers and lists
    """
    # TODO: need to warn user to use seperate cache folder and
    # block list per search

    # Init TODO: parse CLI to do this.
    search_terms = SearchConfig(['Python', 'Scientist'], 'ON', None, 'waterloo', 25)
    config = JobFunnelConfig(
        't_m.csv', 't_udnl.json', 't_gdnl.json', './t_cache',
        search_terms, [IndeedScraperCAEng], 't_log.log',
        log_level=logging.INFO,
    )
    JobFunnel(config).run()


if __name__ == '__main__':
    main()
