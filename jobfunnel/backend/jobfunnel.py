"""Scrapes jobs, applies search filters and writes pickles to master list
Paul McInnis 2020
"""
import csv
import json
import logging
import os
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from time import time
from typing import Dict, List, Optional, Tuple

from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.tools import Logger
from jobfunnel.backend.tools.filters import DuplicatedJob, JobFilter
from jobfunnel.config import JobFunnelConfigManager
from jobfunnel.resources import (CSV_HEADER, MAX_BLOCK_LIST_DESC_CHARS,
                                 MAX_CPU_WORKERS,
                                 MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH, T_NOW,
                                 DuplicateType, JobStatus, Locale)


class JobFunnel(Logger):
    """Class that initializes a Scraper and scrapes a website to get jobs

    NOTE: This is intended to be used with persistant cache and CSV files
          dedicated to a single, consistant job search.
    TODO: instead of Dic[str, Job] we should be using JobsDict
    """

    def __init__(self, config: JobFunnelConfigManager) -> None:
        """Initialize a JobFunnel object, with a JobFunnel Config

        Args:
            config (JobFunnelConfigManager): config object containing paths etc.
        """
        super().__init__(
            level=config.log_level,
            file_path=config.log_file,
        )
        self.config = config
        self.config.create_dirs()
        self.config.validate()
        self.__date_string = date.today().strftime("%Y-%m-%d")
        self.master_jobs_dict = {}  # type: Dict[str, Job]

        # Open a session with/out a proxy configured
        self.session = Session()
        if self.config.proxy_config:
            self.session.proxies = {
                self.config.proxy_config.protocol: self.config.proxy_config.url
            }

        # Read the user's block list
        user_block_jobs_dict = {}  # type: Dict[str, str]
        if os.path.isfile(self.config.user_block_list_file):
            user_block_jobs_dict = json.load(
                open(self.config.user_block_list_file, 'r')
            )

        # Read the user's duplicate jobs list (from TFIDF)
        duplicate_jobs_dict = {}  # type: Dict[str, str]
        if os.path.isfile(self.config.duplicates_list_file):
            duplicate_jobs_dict = json.load(
                open(self.config.duplicates_list_file, 'r')
            )

        # Initialize our job filter
        self.job_filter = JobFilter(
            user_block_jobs_dict,
            duplicate_jobs_dict,
            self.config.search_config.blocked_company_names,
            T_NOW - timedelta(days=self.config.search_config.max_listing_days),
            log_level=self.config.log_level,
            log_file=self.config.log_file,
        )

    @property
    def daily_cache_file(self) -> str:
        """The name for for pickle file containing the scraped data ran today'
        TODO: instead of using a 'daily' cache file, we should be tying this
        into the search that was made to prevent cross-caching results.
        """
        return os.path.join(
            self.config.cache_folder, f"jobs_{self.__date_string}.pkl",
        )

    def run(self) -> None:
        """Scrape, update lists and save to CSV.
        """
        # Read the master CSV file
        if os.path.isfile(self.config.master_csv_file):
            self.master_jobs_dict = self.read_master_csv()

        # Load master csv jobs if they exist and update our block list with
        # any jobs the user has set the status to == a remove status
        # NOTE: we want to do this first to make our filters use current info.
        if self.master_jobs_dict:
            self.update_user_block_list()
        else:
            logging.debug(
                "No master-CSV present, did not update block-list: "
                f"{self.config.user_block_list_file}"
            )

        # Scrape jobs or load them from a cache if one exists (--no-scrape)
        scraped_jobs_dict = {}  # type: Dict[str, Job]
        if self.config.no_scrape:

            # Load cache since --no-scrape is set
            self.logger.info("Skipping scraping, running with --no-scrape.")
            if os.path.exists(self.daily_cache_file):
                scraped_jobs_dict = self.load_cache(self.daily_cache_file)
            else:
                self.logger.warning(
                    f"No incoming jobs, missing cache: {self.daily_cache_file}"
                )
        else:

            # Scrape new jobs from all our configured providers and cache them
            scraped_jobs_dict = self.scrape()
            self.write_cache(scraped_jobs_dict)

        # Filter out any jobs we have rejected, archived or block-listed
        # NOTE: we do not remove duplicates here as these may trigger updates
        if scraped_jobs_dict:
            scraped_jobs_dict = self.job_filter.filter(
                scraped_jobs_dict, remove_existing_duplicate_keys=False
            )
        if self.master_jobs_dict:
            self.master_jobs_dict = self.job_filter.filter(
                self.master_jobs_dict, remove_existing_duplicate_keys=False,
            )

        # Parse duplicate jobs into updates for master jobs dict
        # FIXME: we need to search for duplicates without master jobs too!
        duplicate_jobs = []  # type: List[DuplicatedJob]
        if self.master_jobs_dict and scraped_jobs_dict:

            # Remove jobs with duplicated key_ids from scrape + update master
            duplicate_jobs = self.job_filter.find_duplicates(
                self.master_jobs_dict, scraped_jobs_dict,
            )

            for match in duplicate_jobs:

                # Was it a key-id match?
                if match.type in [DuplicateType.KEY_ID or
                                  DuplicateType.EXISTING_TFIDF]:

                    # NOTE: original and duplicate have same key id for these.
                    # When it's EXISTING_TFIDF, we can't set match.duplicate
                    # because it is only partially stored in the block list JSON
                    if match.original.key_id and (match.original.key_id
                                                  != match.duplicate.key_id):
                        raise ValueError(
                            "Found duplicate by key-id, but keys dont match! "
                            f"{match.original.key_id}, {match.duplicate.key_id}"
                        )

                    # Got a key-id match, pop from scrape dict and maybe update
                    upd = self.master_jobs_dict[
                        match.duplicate.key_id].update_if_newer(
                            scraped_jobs_dict.pop(match.duplicate.key_id)
                    )
                    self.logger.debug(
                        f"Identified duplicate {match.duplicate.key_id} and "
                        f"{'updated older' if upd else 'did not update'} "
                        f"original job of same key-id with its data."
                    )

                # Was it a content-match?
                elif match.type == DuplicateType.NEW_TFIDF:

                    # Got a content match, pop from scrape dict and maybe update
                    upd = self.master_jobs_dict[
                        match.original.key_id].update_if_newer(
                            scraped_jobs_dict.pop(match.duplicate.key_id)
                        )
                    self.logger.debug(
                        f"Identified {match.duplicate.key_id} as a "
                        "duplicate by contents and "
                        f"{'updated older' if upd else 'did not update'} "
                        f"original job {match.original.key_id} with its data."
                    )

        # Update duplicates file (if any updates are incoming)
        if duplicate_jobs:
            self.update_duplicates_file()

        # Update master jobs dict with the incoming jobs that passed filters
        if scraped_jobs_dict:
            self.master_jobs_dict.update(scraped_jobs_dict)

        # Write-out to CSV or log messages
        if self.master_jobs_dict:

            # Write our updated jobs out (if none, dont make the file at all)
            self.write_master_csv(self.master_jobs_dict)
            self.logger.info(
                f"Done. View your current jobs in {self.config.master_csv_file}"
            )

        else:
            # We got no new, unique jobs. This is normal if loading scrape
            # with --no-scrape as all jobs are removed by duplicate filter
            if self.config.no_scrape:
                # User is running --no-scrape probably just to update lists
                self.logger.debug("No new jobs were added.")
            else:
                self.logger.warning("No new jobs were added to CSV.")


    def scrape(self) ->Dict[str, Job]:
        """Run each of the desired Scraper.scrape() with threading and delaying
        """
        self.logger.info(
            f"Scraping local providers with: {self.config.scraper_names}"
        )

        # Iterate thru scrapers and run their scrape.
        jobs = {}  # type: Dict[str, Job]
        for scraper_cls in self.config.scrapers:
            start = time()
            scraper = scraper_cls(self.session, self.config, self.job_filter)
            # TODO: add a warning for overwriting different jobs with same key!
            jobs.update(scraper.scrape())
            end = time()
            self.logger.debug(
                f"Scraped {len(jobs.items())} jobs from {scraper_cls.__name__},"
                f" took {(end - start):.3f}s"
            )

        self.logger.info(f"Completed all scraping, found {len(jobs)} new jobs.")
        return jobs

    def recover(self) -> None:
        """Build a new master CSV from all the available pickles in our cache
        """
        self.logger.info("Recovering jobs from all cache files in cache folder")
        if os.path.exists(self.config.user_block_list_file):
            self.logger.warning(
                "Running recovery mode, but with existing block-list, delete "
                f"{self.config.user_block_list_file} if you want to start fresh"
                " from the cached data and not filter any jobs away."
            )
        all_jobs_dict = {}  # type: Dict[str, Job]
        for file in os.listdir(self.config.cache_folder):
            if '.pkl' in file:
                all_jobs_dict.update(
                    self.load_cache(
                        os.path.join(self.config.cache_folder, file)
                    )
                )
        self.write_master_csv(self.job_filter.filter(all_jobs_dict))

    def load_cache(self, cache_file: str) -> Dict[str, Job]:

        """Load today's scrape data from pickle via date string

        TODO: search the cache for pickles that match search config.
        (we may need a registry for the pickles and seach terms used)

        Args:
            cache_file (str): path to cache pickle file containing jobs dict
                keyed by Job.KEY_ID.

        Raises:
            FileNotFoundError: if cache file is missing

        Returns:
            Dict[str, Job]: [description]
        """
        if not os.path.exists(cache_file):
            raise FileNotFoundError(
                f"{cache_file} not found! Have you scraped any jobs today?"
            )
        else:
            jobs_dict = pickle.load(open(cache_file, 'rb'))
            self.logger.info(
                f"Read {len(jobs_dict.keys())} jobs from previously-scraped "
                f"jobs cache: {cache_file}."
            )
            self.logger.debug(
                "NOTE: you may see many duplicate IDs detected if these jobs "
                "exist in your master CSV already."
            )
            return jobs_dict

    def write_cache(self, jobs_dict: Dict[str, Job],
                    cache_file: str = None) -> None:
        """Dump a jobs_dict into a pickle

        TODO: write search_config into the cache file and jobfunnel version
        TODO: some way to cache Job.RAW without hitting recursion limit
        FIXME: add versioning to this

        Args:
            jobs_dict (Dict[str, Job]): jobs dict to dump into cache.
            cache_file (str, optional): file path to write to. Defaults to None.
        """
        cache_file = cache_file if cache_file else self.daily_cache_file
        for job in jobs_dict.values():
            job._raw_scrape_data = None
        pickle.dump(jobs_dict, open(cache_file, 'wb'))
        self.logger.debug(
            f"Dumped {len(jobs_dict.keys())} jobs to {cache_file}"
        )

    def read_master_csv(self) -> Dict[str, Job]:
        """Read in the master-list CSV to a dict of unique Jobs

        TODO: make blurb --> description and add short_description

        Returns:
            Dict[str, Job]: unique Job objects in the CSV
        """
        jobs_dict = {}  # type: Dict[str, Job]
        with open(self.config.master_csv_file, 'r', encoding='utf8',
                  errors='ignore') as csvfile:
            for row in csv.DictReader(csvfile):

                # NOTE: we are doing legacy support here with 'blurb' etc.
                # In the future we should have an actual short description
                if 'short_description' in row:
                    short_description = row['short_description']
                else:
                    short_description = ''
                post_date = datetime.strptime(row['date'], '%Y-%m-%d')

                if 'scrape_date' in row:
                    scrape_date = datetime.strptime(
                        row['scrape_date'], '%Y-%m-%d'
                    )
                else:
                    scrape_date = post_date

                if 'raw' in row:
                    # NOTE: we should never see this because raw cant be in CSV
                    raw = row['raw']
                else:
                    raw = None

                # We need to convert from user statuses
                status = None
                if 'status' in row:
                    status_str = row['status'].strip()
                    for p_status in JobStatus:
                        if status_str.lower() == p_status.name.lower():
                            status = p_status
                            break
                if not status:
                    self.logger.warning(
                        f"Unknown status {status_str}, setting to UNKNOWN"
                    )
                    status = JobStatus.UNKNOWN

                # NOTE: this is for legacy support:
                locale = None
                if 'locale' in row:
                    locale_str = row['locale'].strip()
                    for p_locale in Locale:
                        if locale_str.lower() == p_locale.name.lower():
                            locale = p_locale
                            break
                if not locale:
                    self.logger.warning(
                        f"Unknown locale {locale_str}, setting to UNKNOWN"
                    )
                    locale = locale.UNKNOWN

                job = Job(
                    title=row['title'],
                    company=row['company'],
                    location=row['location'],
                    description=row['blurb'],
                    key_id=row['id'],
                    url=row['link'],
                    locale=locale,
                    query=row['query'],
                    status=status,
                    provider=row['provider'],
                    short_description=short_description,
                    post_date=post_date,
                    scrape_date=scrape_date,
                    raw=raw,
                    tags=row['tags'].split(','),
                )
                job.validate()
                jobs_dict[job.key_id] = job

        self.logger.debug(
            f"Read {len(jobs_dict.keys())} jobs from master-CSV: "
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
                writer.writerow(job.as_row)
        self.logger.debug(
            f"Wrote {len(jobs)} jobs to {self.config.master_csv_file}"
        )

    def update_user_block_list(self) -> None:
        """From data in master CSV file, add jobs with removeable statuses to
        our configured user block list file and save (if any)

        NOTE: adding jobs to block list will result in filter() removing them
        from all scraped & cached jobs in the future (persistant).

        Raises:
            FileNotFoundError: if no master_jobs_dict is provided and master csv
                               file does not exist.
        """

        # Try to load from CSV if master_jobs_dict is un-set
        if not self.master_jobs_dict:
            if os.path.isfile(self.config.master_csv_file):
                self.master_jobs_dict or self.read_master_csv()
            else:
                raise FileNotFoundError(
                    f"Cannot update {self.config.user_block_list_file} without "
                    f"{self.config.master_csv_file}"
                )

        # Add jobs from csv that need to be filtered away, if any + update self
        n_jobs_added = 0
        for job in self.master_jobs_dict.values():
            if job.is_remove_status:
                if job.key_id not in self.job_filter.user_block_jobs_dict:
                    n_jobs_added += 1
                    self.job_filter.user_block_jobs_dict[
                        job.key_id] = job.as_json_entry
                    logging.info(
                        f'Added {job.key_id} to '
                        f'{self.config.user_block_list_file}'
                    )
                else:
                    self.logger.warning(
                        f"Job {job.key_id} has been set to a removable status "
                        "and removed from master CSV multiple times."
                    )

        if n_jobs_added:
            # Write out complete list with any additions from the masterlist
            # NOTE: we use indent=4 so that it stays human-readable.
            with open(self.config.user_block_list_file, 'w',
                      encoding='utf8') as outfile:
                outfile.write(
                    json.dumps(
                        self.job_filter.user_block_jobs_dict,
                        indent=4,
                        sort_keys=True,
                        separators=(',', ': '),
                        ensure_ascii=False,
                    )
                )

            self.logger.info(
                f"Moved {n_jobs_added} jobs into block-list due to removable "
                f"statuses: {self.config.user_block_list_file}"
            )

    def update_duplicates_file(self) -> None:
        """Update duplicates filter file if we have a path and contents
        TODO: this should be writing out DuplicatedJob objects and a version
        so that we retain links to original jobs.
        """
        if self.config.duplicates_list_file:
            if self.job_filter.duplicate_jobs_dict:

                # Write out the changes NOTE: indent=4 is for human-readability
                self.logger.debug("Extending existing duplicate jobs dict.")
                with open(self.config.duplicates_list_file, 'w',
                          encoding='utf8') as outfile:
                    outfile.write(
                        json.dumps(
                            self.job_filter.duplicate_jobs_dict,
                            indent=4,
                            sort_keys=True,
                            separators=(',', ': '),
                            ensure_ascii=False,
                        )
                    )
            else:
                self.logger.debug(
                    "Current duplicate jobs dict is empty, no updates written."
                )
        else:
            self.logger.warning(
                "Duplicates will not be saved, no duplicates list "
                "file set. Saving to a duplicates file will ensure "
                "that jobs detected to be duplicates by contents persist."
            )
