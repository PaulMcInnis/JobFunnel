#!python
"""Builds a config from CLI, runs desired scrapers and updates JSON + CSV

NOTE: you can test this from cloned source by running python -m jobfunnel

TODO/FIXME:
    * make it easier to continue an existing search
    * make it easier to run multiple searches at once w.r.t caching
    * simplified CLI args with new --recover and --clean options
    * add warning around seperate cache folders blocklists per search
    * document API usage in readme
    ** add back the duplicates JSON
"""
import argparse
import sys
from typing import Union
import logging

from .backend.jobfunnel import JobFunnel
from .config import parse_config, validate_config, build_funnel_cfg_from_legacy


def main():
    """Parse CLI and call jobfunnel() to manage scrapers and lists
    """
    # Parse CLI into a dict
    config = parse_config()
    validate_config(config)
    funnel_cfg = build_funnel_cfg_from_legacy(config)
    job_funnel = JobFunnel(funnel_cfg)
    job_funnel.run()


if __name__ == '__main__':
    main()
