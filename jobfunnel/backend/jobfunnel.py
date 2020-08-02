"""Paul McInnis 2018
Scrapes jobs, applies search filters and writes pickles to master list
"""

import csv
from collections import OrderedDict
from datetime import date, datetime
import json
import logging
import os
import pickle
from requests import Session
import sys
from typing import Dict, List, Union
from time import time

from jobfunnel.config import JobFunnelConfig
from jobfunnel.backend import Job
from jobfunnel.resources.resources import CSV_HEADER, REMOVE_STATUSES


class JobFunnel(object):
    """Class that initializes a Scraper and scrapes a website to get jobs
    """

    def __init__(self, config: JobFunnelConfig):
        """Initialize a JobFunnel object, with a JobFunnel Config

        Args:
            config (JobFunnelConfig): config object containing paths etc.
        """
        self.config = config
        self.config.create_dirs()
        self.config.validate()
        self.date_string = date.today().strftime("%Y-%m-%d")
        self.logger = None
        self.init_logging()

        # Open a session with/out a proxy configured
        self.session = Session()
        if self.config.proxy_config:
            self.session.proxies = {
                self.config.proxy_config.protocol: self.config.proxy_config.url
            }

    def run(self) -> None:
        """Scrape, update lists and save to CSV.
        """
        # Parse the master list path to update filter list
        self.update_user_deny_list()

        # Get new jobs keyed by their unique ID
        jobs_dict = self.scrape()  # type: Dict[str, Job]

        # Filter out scraped jobs we have rejected, archived or blacklisted
        # (before we add them to the CSV)
        self.filter_excluded_jobs(jobs_dict)

        # Load and update existing masterlist
        if os.path.exists(self.config.master_csv_file):
            # open masterlist if it exists & init updated masterlist
            masterlist = self.read_master_csv()  # type: Dict[str, Job]

            # update masterlist to remove filtered/blacklisted jobs
            self.filter_excluded_jobs(jobs_dict)
            # n_filtered += tfidf_filter(jobs_dict, masterlist)  # FIXME
            masterlist.update(jobs_dict)

            # save
            self.write_master_csv(jobs_dict)

        else:
            # run tfidf filter on initial scrape
            # n_filtered += tfidf_filter(jobs_dict, masterlist)  # FIXME

            # dump the results into the data folder as the masterlist
            self.write_master_csv(jobs_dict)
            self.logger.info(
                f'no masterlist detected, added {len(jobs_dict.keys())}'
                f' jobs to {self.config.master_csv_file}'
            )

        self.logger.info(
            f"Done. View your current jobs in {self.config.master_csv_file}"
        )

    def init_logging(self) -> None:
        """Initialize a logger
        TODO: we are mixing logging calls with self.logger here, is that OK?
        """
        self.logger = logging.getLogger()
        self.logger.setLevel(self.config.log_level)
        logging.basicConfig(
            filename=self.config.log_file,
            level=self.config.log_level,
        )
        if self.config.log_level == 20:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        else:
            logging.getLogger().addHandler(logging.StreamHandler())
        self.logger.info(f"jobfunnel initialized at {self.date_string}")

    def scrape(self) ->Dict[str, Job]:
        """Run each of the desired Scraper.scrape() with threading and delaying
        """
        if self.config.no_scrape:
            self.logger.info("Bypassing scraping (--no-scrape).")
            return
        self.logger.info(f"Starting scraping for: {self.config.scraper_names}")

        # Iterate thru scrapers and run their scrape.
        jobs = {}  # type: Dict[str, Job]
        for scraper_cls in self.config.scrapers:
            # FIXME: need the threader and delay here
            start = time()
            scraper = scraper_cls(
                self.session, self.config.search_terms, self.logger
            )
            # TODO: warning for overwriting different jobs with same key
            jobs.update(scraper.scrape())
            end = time()
            self.logger.info(
                f"Scraped {len(jobs.items())} jobs from {scraper_cls.__name__},"
                f" took {(end - start):.3f}s'"
            )

        self.logger.info(f"Completed Scraping, got {len(jobs)} jobs.")
        return jobs

    def recover(self):
        """Build a new master CSV from all the available pickles in our cache
        """
        # FIXME: impl. should read all the pickles and make a new masterlist
        pass

    @property
    def daily_pickle_file(self) -> str:
        """The name for for pickle file containing the scraped data ran today
        """
        return os.path.join(
            self.config.data_path, f"jobs_{self.date_string}.pkl",
        )

    def load_pickle(self) -> Dict[str, Job]:
        """Load today's scrape data from pickle via date string
        """
        try:
            jobs_dict = pickle.load(open(self.daily_pickle_file, 'rb'))
        except FileNotFoundError as e:
            self.logger.error(
                f"{self.daily_pickle_file} not found! Have you scraped any jobs"
                " today?"
            )
            raise e
        self.logger.info(
            f"Loaded {len(jobs_dict.keys())} jobs from {self.daily_pickle_file}"
        )
        return jobs_dict

    def dump_pickle(self, jobs_dict: Dict[str, Job]) -> None:
        """Dump a pickle of the daily scrape dict
        """
        pickle.dump(jobs_dict, open(self.daily_pickle_file, 'wb'))
        n_jobs = 2 # FIXME
        self.logger.info(
            f"Dumped {n_jobs} jobs to {self.daily_pickle_file}"
        )

    def read_master_csv(self) -> Dict[str, Job]:
        """Read in the master-list CSV to a dict of unique Jobs

        Args:
            key_by_id (bool, optional): key jobs by ID, return as a List[Job] if
                False. Defaults to True.1

        TODO: update from legacy CSV header for short & long description

        Returns:
            Dict[str, Job]: unique Job objects in the CSV
        """
        with open(self.config.master_csv_file, 'r', encoding='utf8',
                  errors='ignore') as csvfile:

            jobs_dict = {}  # type: Dict[str, Job]
            for row in csv.DictReader(csvfile):
                # NOTE: this is for legacy support:
                locale = row['locale'] if 'locale' in row else ''
                if 'description' in row:
                    short_description = row['description']
                else:
                    short_description = ''
                if 'scrape_date' in row:
                    scrape_date = datetime.fromisoformat(row['scrape_date'])
                else:
                    scrape_date = datetime(1970, 1, 1)
                if 'raw' in row:
                    raw = row['raw']
                else:
                    raw = None
                job = Job(
                    title=row['title'],
                    company=row['company'],
                    location=row['location'],
                    description=row['blurb'],
                    key_id=row['id'],
                    url=row['link'],
                    locale=locale,
                    query=row['query'],
                    status=row['status'],
                    provider=row['provider'],
                    short_description=short_description,
                    post_date=row['date'],
                    scrape_date=scrape_date,
                    raw=raw,
                    tags=row['tags'].split(','),
                )
                job.validate()
                jobs_dict[job.key_id] = job

        self.logger.info(
            f"Read out {len(jobs_dict.keys())} jobs from "
            f"{self.config.master_csv_file}"
        )
        return jobs_dict

    def write_master_csv(self, jobs: Dict[str, Job]) -> None:
        """Write out our dict of unique Jobs to a CSV

        Args:
            jobs (Dict[str, Job]): Dict of unique Jobs, keyd by unique id's
        """
        with open(self.config.master_csv_file, 'w', encoding='utf8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
            writer.writeheader()
            for job in jobs.values():
                job.validate()
                writer.writerow(job.get_csv_row())
        n_jobs = len(jobs)
        self.logger.info(
            f"Wrote out {n_jobs} jobs to {self.config.master_csv_file}"
        )

    def update_user_deny_list(self):
        """Read the master CSV file and pop jobs by status into our user deny
        list (which is a JSON)
        """
        # FIXME: impl.
        self.logger.info(f"Updated {self.config.user_deny_list_file}")

    def filter_excluded_jobs(self, jobs_dict: Dict[str, Job]) -> int:
        """Load the user's deny-list if it exists and pop any matching jobs by
        key
        Returns the number of filtered jobs
        NOTE: modifies in-place
        FIXME: load the company deny-list as well
        """
        n_filtered = 0
        if os.path.isfile(self.config.user_deny_list_file):
            deny_dict = json.load(
                open(self.config.user_deny_list_file, 'r')
            )
            for jobid in deny_dict:
                if jobid in jobs_dict:
                    jobs_dict.pop(jobid)
                    n_filtered += 1
            self.logger.info(
                f'removed {n_filtered} jobs present in filter-list'
            )
        else:
            self.logger.warning(
                f'No jobs filtered, missing: {self.config.user_deny_list_file}'
            )
        return n_filtered
