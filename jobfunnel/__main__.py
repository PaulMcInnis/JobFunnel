#!python
"""Builds a config from CLI, runs desired scrapers and updates JSON + CSV
"""
import os
import sys

from .backend.jobfunnel import JobFunnel
from .config import build_config_dict, get_config_manager, parse_cli


def main():
    """Parse CLI and call jobfunnel() to manage scrapers and lists"""
    # Parse CLI into validated schema
    args = parse_cli(sys.argv[1:])
    cfg_dict = build_config_dict(args)

    # Build config manager
    funnel_cfg = get_config_manager(cfg_dict)
    funnel_cfg.create_dirs()

    # Init
    job_funnel = JobFunnel(funnel_cfg)

    # Run or recover
    if args["do_recovery_mode"]:
        job_funnel.recover()
    else:
        job_funnel.run()

    # Return value for Travis CI
    if len(job_funnel.master_jobs_dict.keys()) > 1 and os.path.exists(
        funnel_cfg.master_csv_file
    ):
        return 0
    else:
        return 1


if __name__ == "__main__":
    main()
