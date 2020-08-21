"""Paul McInnis 2020
Scrapes jobs, applies search filters and writes pickles to master list
"""
import csv
import json
import logging
import os
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from time import time
from typing import Dict, List

from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.tools.filters import job_is_old, tfidf_filter
from jobfunnel.config import JobFunnelConfig
from jobfunnel.resources import (CSV_HEADER, MAX_BLOCK_LIST_DESC_CHARS,
                                 MAX_CPU_WORKERS, JobStatus, Locale)


class JobFunnel:
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
        self.logger = None
        self.__date_string = date.today().strftime("%Y-%m-%d")
        self.init_logging()

        # Open a session with/out a proxy configured
        self.session = Session()
        if self.config.proxy_config:
            self.session.proxies = {
                self.config.proxy_config.protocol: self.config.proxy_config.url
            }

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
        NOTE: we are assuming the user has distinct cache folder per-search,
        otherwise we will load the cache for today, for a different search!
        """
        # Parse the master list path to update our block list
        # NOTE: we want to do this first to ensure scraping is efficient when
        # we are getting detailed job information (per-job)
        self.update_block_list()

        # Get jobs keyed by their unique ID, use cache if we scraped today
        jobs_dict = {}  # type: Dict[str, Job]
        if os.path.exists(self.daily_cache_file):
            jobs_dict = self.load_cache(self.daily_cache_file)
        elif self.config.no_scrape:
            self.logger.warning(
                f"No jobs cached, missing: {self.daily_cache_file}"
            )

        if self.config.no_scrape:
            self.logger.info("Skipping scraping, running with --no-scrape.")
        else:
            jobs_dict = self.scrape()  # type: Dict[str, Job]
            self.write_cache(jobs_dict)

        # Filter out scraped jobs we have rejected, archived or block-listed
        # (before we add them to the CSV)
        self.filter(jobs_dict)

        # Load and update existing masterlist
        if os.path.exists(self.config.master_csv_file):

            # Identify duplicate jobs using the existing masterlist
            masterlist = self.read_master_csv()  # type: Dict[str, Job]
            self.filter(masterlist)  # NOTE: this reduces size of masterlist
            try:
                tfidf_filter(jobs_dict, masterlist)
            except ValueError as err:
                self.logger.error(
                    f"Skipping similarity filter due to: {str(err)}"
                )

            # Expand the masterlist with filters, non-duplicated jobs & save
            masterlist.update(jobs_dict)
            self.write_master_csv(masterlist)

        else:
            # FIXME: we should still remove duplicates within jobs_dict?
            # Dump the results into the data folder as the masterlist
            self.write_master_csv(jobs_dict)

        self.logger.info(
            f"Done. View your current jobs in {self.config.master_csv_file}"
        )

    def init_logging(self) -> None:
        """Initialize a logger
        NOTE: make stdout format more configurable?
        """
        self.logger = logging.getLogger('jobfunnel')
        self.logger.setLevel(self.config.log_level)
        logging.basicConfig(
            filename=self.config.log_file,
            level=self.config.log_level,
        )
        formatter = logging.Formatter('[%(levelname)s] jobfunnel: %(message)s')
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        self.logger.addHandler(stdout_handler)
        self.logger.info(f"JobFunnel initialized at {self.__date_string}")

    def scrape(self) ->Dict[str, Job]:
        """Run each of the desired Scraper.scrape() with threading and delaying
        """
        self.logger.info(f"Starting scraping for: {self.config.scraper_names}")

        # Iterate thru scrapers and run their scrape.
        jobs = {}  # type: Dict[str, Job]
        for scraper_cls in self.config.scrapers:
            # FIXME: need to add the threader and delaying here
            start = time()
            scraper = scraper_cls(self.session, self.config)
            # TODO: add a warning for overwriting different jobs with same key
            jobs.update(scraper.scrape())
            end = time()
            self.logger.info(
                f"Scraped {len(jobs.items())} jobs from {scraper_cls.__name__},"
                f" took {(end - start):.3f}s"
            )

        self.logger.info(f"Completed all scraping, found {len(jobs)} new jobs.")
        return jobs

    def recover(self):
        """Build a new master CSV from all the available pickles in our cache
        """
        self.logger.info("Recovering jobs from all cache files in cache folder")
        if os.path.exists(self.config.user_block_list_file):
            self.logger.warning(
                "Running recovery mode, but with existing block-list, delete "
                f"{self.config.user_block_list_file} if you want to start fresh"
                " from the cached data and not filter any jobs away."
            )
        all_jobs_dict = {}
        for file in os.listdir(self.config.cache_folder):
            if '.pkl' in file:
                all_jobs_dict.update(
                    self.load_cache(
                        os.path.join(self.config.cache_folder, file)
                    )
                )
        self.filter(all_jobs_dict)
        self.write_master_csv(all_jobs_dict)

    def load_cache(self, cache_file: str) -> Dict[str, Job]:
        """Load today's scrape data from pickle via date string
        TODO: search the cache for pickles that match search config.
        (we may need a registry for the pickles and seach terms used)
        """
        try:
            jobs_dict = pickle.load(open(cache_file, 'rb'))
        except FileNotFoundError as e:
            self.logger.error(
                f"{cache_file} not found! Have you scraped any jobs today?"
            )
            raise e
        self.logger.info(
            f"Read {len(jobs_dict.keys())} cached jobs from: {cache_file}"
        )
        return jobs_dict

    def write_cache(self, jobs_dict: Dict[str, Job],
                    cache_file: str = None) -> None:
        """Dump a jobs_dict into a pickle
        TODO: write search_config into the cache file and jobfunnel version
        FIXME: some way to cache raw data without recur-limit
        """
        cache_file = cache_file if cache_file else self.daily_cache_file
        pickle.dump(jobs_dict, open(cache_file, 'wb'))
        self.logger.info(
            f"Dumped {len(jobs_dict.keys())} jobs to {cache_file}"
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
        jobs_dict = {}  # type: Dict[str, Job]
        with open(self.config.master_csv_file, 'r', encoding='utf8',
                  errors='ignore') as csvfile:
            for row in csv.DictReader(csvfile):
                # NOTE: we are doing legacy support here with 'blurb' etc.
                if 'description' in row:
                    short_description = row['description']
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
                    raw = row['raw']
                else:
                    raw = None

                # We need to convert from user statuses
                # TODO: put this in Job?
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

        self.logger.info(
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
        self.logger.info(
            f"Wrote {len(jobs)} jobs to {self.config.master_csv_file}"
        )

    def update_block_list(self):
        """Read the master CSV file and pop jobs by status into our user block
        list (which is a JSON).

        NOTE: adding jobs to block list will result in filter() removing them
        from all scraped & cached jobs in the future.

        NOTE: we truncate descriptions in the block list
        """
        if os.path.isfile(self.config.master_csv_file):

            # Load existing filtered jobs, if any
            if os.path.isfile(self.config.user_block_list_file):
                blocked_jobs_dict = json.load(
                    open(self.config.user_block_list_file, 'r')
                )
            else:
                blocked_jobs_dict = {}

            # Add jobs from csv that need to be filtered away, if any
            n_jobs_added = 0
            for job in self.read_master_csv().values():
                if job.is_remove_status and job.key_id not in blocked_jobs_dict:
                    n_jobs_added += 1
                    logging.info(
                        f'Added {job.key_id} to '
                        f'{self.config.user_block_list_file}'
                    )
                    blocked_jobs_dict[job.key_id] = {
                        'title': job.title,
                        'post_date': job.post_date.strftime('%Y-%m-%d'),
                        'description': (
                                job.description[:MAX_BLOCK_LIST_DESC_CHARS]
                                + '..'
                            )
                            if len(job.description) > MAX_BLOCK_LIST_DESC_CHARS
                            else job.description,
                        'status': job.status.name,
                    }

            # Write out complete list with any additions from the masterlist
            # NOTE: we use indent=4 so that it stays human-readable.
            with open(self.config.user_block_list_file, 'w',
                      encoding='utf8') as outfile:
                outfile.write(
                    json.dumps(
                        blocked_jobs_dict,
                        indent=4,
                        sort_keys=True,
                        separators=(',', ': '),
                        ensure_ascii=False,
                    )
                )
            self.logger.info(
                f"Added {n_jobs_added} jobs to block-list: "
                f"{self.config.user_block_list_file}"
            )
        else:
            logging.info(
                "No master-CSV present, did not update block-list: "
                f"{self.config.user_block_list_file}"
            )

    def filter(self, jobs_dict: Dict[str, Job]) -> int:
        """Remove jobs from jobs_dict if they are:
            1. in our block-list
            2. status == a removal status string (i.e. DELETE)
            3. job.company == one of our blocked company names

        Returns the number of filtered jobs

        TODO: would be cool if we could run TFIDF in here too
        FIXME: load the global block-list as well
        """
        # Read the user's block list
        block_dict = {}  # type: Dict[str, Job]
        if os.path.isfile(self.config.user_block_list_file):
            block_dict = json.load(
                open(self.config.user_block_list_file, 'r')
            )

        # Read the user's duplicate jobs list (from TFIDF)
        duplicates_dict = {}  # type: Dict[str, Job]
        if os.path.isfile(self.config.duplicates_list_file):
            duplicates_dict = json.load(
                open(self.config.user_block_list_file, 'r')
            )

        # Filter jobs out using all our available filters
        # NOTE: checks are arranged in order of assumed calculation expense
        filter_jobs_ids = []
        for key_id, job in jobs_dict.items():
            if (job.is_remove_status
                or job.company in self.config.search_config.blocked_company_names
                or key_id in block_dict
                or key_id in duplicates_dict
                or job_is_old(job, self.config.search_config.max_listing_days)):
                filter_jobs_ids.append(key_id)

        for key_id in filter_jobs_ids:
            jobs_dict.pop(key_id)

        n_filtered = len(filter_jobs_ids)
        if n_filtered > 0:
            self.logger.info(f'Filtered-out {n_filtered} jobs from results.')
        else:
            # TODO: print a % of jobs that are new /etc here.
            self.logger.info(f'No jobs were filtered from results.')

        return n_filtered
