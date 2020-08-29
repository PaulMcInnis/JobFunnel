#!python
"""Builds a config from CLI, runs desired scrapers and updates JSON + CSV

NOTE: you can test this from cloned source by running python -m jobfunnel
"""
import argparse
import sys
from typing import Union
import logging

from .backend.jobfunnel import JobFunnel
from .config import parse_cli, config_builder


def main():
    """Parse CLI and call jobfunnel() to manage scrapers and lists
    """
    # Parse CLI into a dict
    args = parse_cli()
    do_recovery_mode = args.do_recovery_mode  # NOTE: we modify args for config
    funnel_cfg = config_builder(args)
    job_funnel = JobFunnel(funnel_cfg)
    if do_recovery_mode:
        job_funnel.recover()
    else:
        job_funnel.run()


if __name__ == '__main__':
    main()
