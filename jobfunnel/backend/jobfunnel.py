"""Scrapes jobs, applies search filters and writes pickles to master list
Paul McInnis 2020
"""

import csv
from datetime import date, datetime, timedelta
import json
import os
import pickle
from time import time
from typing import Dict

from requests import Session

from jobfunnel import __version__
from jobfunnel.backend import Job
from jobfunnel.backend.tools import Logger
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.config import JobFunnelConfigManager
from jobfunnel.resources import (
    CSV_HEADER,
    T_NOW,
    DuplicateType,
    JobStatus,
    Locale,
    Remoteness,
)


class JobFunnel(Logger):
    """Class that initializes a Scraper and scrapes a website to get jobs"""

    def __init__(self, config: JobFunnelConfigManager) -> None:
        """Initialize a JobFunnel object, with a JobFunnel Config

        Args:
            config (JobFunnelConfigManager): config object containing paths etc.
        """
        config.validate()  # NOTE: this ensures log file path exists
        super().__init__(level=config.log_level, file_path=config.log_file)
        self.config = config
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
                open(self.config.user_block_list_file, "r")
            )

        # Read the user's duplicate jobs list (from TFIDF)
        duplicate_jobs_dict = {}  # type: Dict[str, str]
        if os.path.isfile(self.config.duplicates_list_file):
            duplicate_jobs_dict = json.load(open(self.config.duplicates_list_file, "r"))

        # Initialize our job filter
        self.job_filter = JobFilter(
            user_block_jobs_dict,
            duplicate_jobs_dict,
            self.config.search_config.blocked_company_names,
            T_NOW - timedelta(days=self.config.search_config.max_listing_days),
            desired_remoteness=self.config.search_config.remoteness,
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
            self.config.cache_folder,
            f"jobs_{self.__date_string}.pkl",
        )

    def run(self) -> None:
        """Scrape, update lists and save to CSV."""
        # Read the master CSV file
        if os.path.isfile(self.config.master_csv_file):
            self.master_jobs_dict = self.read_master_csv()

        # Load master csv jobs if they exist and update our block list with
        # any jobs the user has set the status to == a remove status
        # NOTE: we want to do this first to make our filters use current info.
        if self.master_jobs_dict:
            self.update_user_block_list()
        else:
            self.logger.debug(
                "No master-CSV present, did not update block-list: %s",
                self.config.user_block_list_file,
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
                    "No incoming jobs, missing cache: %s", self.daily_cache_file
                )
        else:
            # Scrape new jobs from all our configured providers and cache them
            scraped_jobs_dict = self.scrape()

        # Filter out any jobs we have rejected, archived or block-listed
        # NOTE: we do not remove duplicates here as these may trigger updates
        if scraped_jobs_dict:
            self.write_cache(scraped_jobs_dict)
            scraped_jobs_dict = self.job_filter.filter(
                scraped_jobs_dict, remove_existing_duplicate_keys=False
            )
        if self.master_jobs_dict:
            self.master_jobs_dict = self.job_filter.filter(
                self.master_jobs_dict,
                remove_existing_duplicate_keys=False,
            )

        # Parse duplicate jobs into updates for master jobs dict
        # NOTE: we prevent inter-scrape duplicates by key-id within BaseScraper
        # FIXME: impl. TFIDF on inter-scrape duplicates
        duplicate_jobs = []  # type: List[DuplicatedJob]
        if self.master_jobs_dict and scraped_jobs_dict:
            # Remove jobs with duplicated key_ids from scrape + update master
            duplicate_jobs = self.job_filter.find_duplicates(
                self.master_jobs_dict,
                scraped_jobs_dict,
            )

            for match in duplicate_jobs:
                # Was it a key-id match?
                if match.type in [DuplicateType.KEY_ID or DuplicateType.EXISTING_TFIDF]:
                    # NOTE: original and duplicate have same key id for these.
                    # When it's EXISTING_TFIDF, we can't set match.duplicate
                    # because it is only partially stored in the block list JSON
                    if match.original.key_id and (
                        match.original.key_id != match.duplicate.key_id
                    ):
                        raise ValueError(
                            "Found duplicate by key-id, but keys dont match! "
                            f"{match.original.key_id}, {match.duplicate.key_id}"
                        )

                    # Got a key-id match, pop from scrape dict and maybe update
                    upd = self.master_jobs_dict[match.duplicate.key_id].update_if_newer(
                        scraped_jobs_dict.pop(match.duplicate.key_id)
                    )

                    self.logger.debug(
                        "Identified duplicate %s by key-id and %s original job "
                        "with its data.",
                        match.duplicate.key_id,
                        "updated older" if upd else "did not update",
                    )

                # Was it a content-match?
                elif match.type == DuplicateType.NEW_TFIDF:
                    # Got a content match, pop from scrape dict and maybe update
                    upd = self.master_jobs_dict[match.original.key_id].update_if_newer(
                        scraped_jobs_dict.pop(match.duplicate.key_id)
                    )
                    self.logger.debug(
                        "Identified %s as a duplicate by description and %s "
                        "original job %s with its data.",
                        match.duplicate.key_id,
                        "updated older" if upd else "did not update",
                        match.original.key_id,
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
                "Done. View your current jobs in %s", self.config.master_csv_file
            )

        else:
            # We got no new, unique jobs. This is normal if loading scrape
            # with --no-scrape as all jobs are removed by duplicate filter
            if self.config.no_scrape:
                # User is running --no-scrape probably just to update lists
                self.logger.debug("No new jobs were added.")
            else:
                self.logger.warning("No new jobs were added to CSV.")

    def _check_for_inter_scraper_validity(
        self,
        existing_jobs: Dict[str, Job],
        incoming_jobs: Dict[str, Job],
    ) -> None:
        """Verify that we aren't overwriting jobs by key-id between scrapers
        NOTE: this is a slow check, would be cool to improve the O(n) on this
        """
        existing_job_keys = existing_jobs.keys()
        for inc_key_id in incoming_jobs.keys():
            for exist_key_id in existing_job_keys:
                if inc_key_id == exist_key_id:
                    raise ValueError(f"Inter-scraper key-id duplicate! {exist_key_id}")

    def scrape(self) -> Dict[str, Job]:
        """Run each of the desired Scraper.scrape() with threading and delaying"""
        self.logger.info("Scraping local providers with: %s", self.config.scraper_names)

        # Iterate thru scrapers and run their scrape.
        jobs = {}  # type: Dict[str, Job]
        for scraper_cls in self.config.scrapers:
            incoming_jobs_dict = {}
            start = time()
            scraper = scraper_cls(self.session, self.config, self.job_filter)
            try:
                incoming_jobs_dict = scraper.scrape()
            except Exception as e:
                self.logger.error(
                    f"Failed to scrape jobs for {scraper_cls.__name__}: {e}"
                )

            # Ensure we have no duplicates between our scrapers by key-id
            # (since we are updating the jobs dict with results)
            self._check_for_inter_scraper_validity(
                jobs,
                incoming_jobs_dict,
            )

            jobs.update(incoming_jobs_dict)
            end = time()
            self.logger.debug(
                "Scraped %d jobs from %s, took %.3fs",
                len(jobs.items()),
                scraper_cls.__name__,
                (end - start),
            )

        self.logger.info("Completed all scraping, found %d new jobs.", len(jobs))
        return jobs

    def recover(self) -> None:
        """Build a new master CSV from all the available pickles in our cache"""
        self.logger.info("Recovering jobs from all cache files in cache folder")
        if os.path.exists(self.config.user_block_list_file):
            self.logger.warning(
                "Running recovery mode, but with existing block-list, delete "
                "%s if you want to start fresh from the cached data and not "
                "filter any jobs away.",
                self.config.user_block_list_file,
            )
        all_jobs_dict = {}  # type: Dict[str, Job]
        for file in os.listdir(self.config.cache_folder):
            if ".pkl" in file:
                all_jobs_dict.update(
                    self.load_cache(os.path.join(self.config.cache_folder, file))
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
            cache_dict = pickle.load(open(cache_file, "rb"))
            jobs_dict = cache_dict["jobs_dict"]
            version = cache_dict["version"]
            if version != __version__:
                # NOTE: this may be an error in the future
                self.logger.warning(
                    "Loaded jobs cache has version mismatch! "
                    "cache version: %s, current version: %s",
                    version,
                    __version__,
                )
            self.logger.info(
                "Read %d jobs from previously-scraped jobs cache: %s.",
                len(jobs_dict.keys()),
                cache_file,
            )
            self.logger.debug(
                "NOTE: you may see many duplicate IDs detected if these jobs "
                "exist in your master CSV already."
            )
            return jobs_dict

    def write_cache(self, jobs_dict: Dict[str, Job], cache_file: str = None) -> None:
        """Dump a jobs_dict into a pickle

        TODO: write search_config into the cache file and jobfunnel version
        TODO: some way to cache Job.RAW without hitting recursion limit

        Args:
            jobs_dict (Dict[str, Job]): jobs dict to dump into cache.
            cache_file (str, optional): file path to write to. Defaults to None.
        """
        cache_file = cache_file if cache_file else self.daily_cache_file
        for job in jobs_dict.values():
            job._raw_scrape_data = None  # pylint: disable=protected-access
        pickle.dump(
            {
                "version": __version__,
                "jobs_dict": jobs_dict,
            },
            open(cache_file, "wb"),
        )
        self.logger.debug("Dumped %d jobs to %s", len(jobs_dict.keys()), cache_file)

    def read_master_csv(self) -> Dict[str, Job]:
        """Read in the master-list CSV to a dict of unique Jobs

        TODO: make blurb --> description and add short_description

        Returns:
            Dict[str, Job]: unique Job objects in the CSV
        """
        jobs_dict = {}  # type: Dict[str, Job]
        with open(
            self.config.master_csv_file, "r", encoding="utf8", errors="ignore"
        ) as csvfile:
            for row in csv.DictReader(csvfile):
                # NOTE: we are doing legacy support here with 'blurb' etc.
                # In the future we should have an actual short description
                if "short_description" in row:
                    short_description = row["short_description"]
                else:
                    short_description = ""
                post_date = datetime.strptime(row["date"], "%Y-%m-%d")

                if "scrape_date" in row:
                    scrape_date = datetime.strptime(row["scrape_date"], "%Y-%m-%d")
                else:
                    scrape_date = post_date

                if "raw" in row:
                    # NOTE: we should never see this because raw cant be in CSV
                    raw = row["raw"]
                else:
                    raw = None

                # FIXME: this is the wrong way to compare row val to Enum.name!
                # We need to convert from user statuses
                status = None
                if "status" in row:
                    status_str = row["status"].strip()
                    for p_status in JobStatus:
                        if status_str.lower() == p_status.name.lower():
                            status = p_status
                            break
                if not status:
                    self.logger.warning(
                        "Unknown status %s, setting to UNKNOWN", status_str
                    )
                    status = JobStatus.UNKNOWN

                # NOTE: this is for legacy support:
                locale = None
                if "locale" in row:
                    locale_str = row["locale"].strip()
                    for p_locale in Locale:
                        if locale_str.lower() == p_locale.name.lower():
                            locale = p_locale
                            break
                if not locale:
                    self.logger.warning(
                        "Unknown locale %s, setting to UNKNOWN", locale_str
                    )
                    locale = locale.UNKNOWN

                # Check for remoteness (handle if not present for legacy)
                remoteness = Remoteness.UNKNOWN
                if "remoteness" in row:
                    remote_str = row["remoteness"].strip()
                    remoteness = Remoteness[remote_str]
                if not locale:
                    self.logger.warning(
                        "Unknown locale %s, setting to UNKNOWN", locale_str
                    )
                    locale = locale.UNKNOWN

                # Check for wage (handle if not present for legacy
                wage = ""
                if "wage" in row:
                    wage = row["wage"].strip()

                job = Job(
                    title=row["title"],
                    company=row["company"],
                    location=row["location"],
                    description=row["blurb"],
                    key_id=row["id"],
                    url=row["link"],
                    locale=locale,
                    query=row["query"],
                    status=status,
                    provider=row["provider"],
                    short_description=short_description,
                    post_date=post_date,
                    scrape_date=scrape_date,
                    wage=wage,
                    raw=raw,
                    tags=row["tags"].split(","),
                    remoteness=remoteness,
                )
                job.validate()
                jobs_dict[job.key_id] = job

        self.logger.debug(
            "Read %d jobs from master-CSV: %s",
            len(jobs_dict.keys()),
            self.config.master_csv_file,
        )
        return jobs_dict

    def write_master_csv(self, jobs: Dict[str, Job]) -> None:
        """Write out our dict of unique Jobs to a CSV

        Args:
            jobs (Dict[str, Job]): Dict of unique Jobs, keyd by unique id's
        """
        with open(self.config.master_csv_file, "w", encoding="utf8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
            writer.writeheader()
            for job in jobs.values():
                job.validate()
                writer.writerow(job.as_row)
        self.logger.debug(
            "Wrote %d jobs to %s",
            len(jobs),
            self.config.master_csv_file,
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
                self.master_jobs_dict = self.read_master_csv()
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
                    self.job_filter.user_block_jobs_dict[job.key_id] = job.as_json_entry
                    self.logger.debug(
                        "Added %s to %s", job.key_id, self.config.user_block_list_file
                    )
                else:
                    # This could happen if we are somehow mishandling block list
                    self.logger.warning(
                        "Job %s has been set to a removable status and removed "
                        "from master CSV multiple times.",
                        job.key_id,
                    )

        if n_jobs_added:
            # Write out complete list with any additions from the masterlist
            # NOTE: we use indent=4 so that it stays human-readable.
            with open(
                self.config.user_block_list_file, "w", encoding="utf8"
            ) as outfile:
                outfile.write(
                    json.dumps(
                        self.job_filter.user_block_jobs_dict,
                        indent=4,
                        sort_keys=True,
                        separators=(",", ": "),
                        ensure_ascii=False,
                    )
                )

            self.logger.info(
                "Moved %d jobs into block-list due to removable statuses: %s",
                n_jobs_added,
                self.config.user_block_list_file,
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
                with open(
                    self.config.duplicates_list_file, "w", encoding="utf8"
                ) as outfile:
                    outfile.write(
                        json.dumps(
                            self.job_filter.duplicate_jobs_dict,
                            indent=4,
                            sort_keys=True,
                            separators=(",", ": "),
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
