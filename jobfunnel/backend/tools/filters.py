"""Filters that are used in jobfunnel's filter() method or as intermediate
filters to reduce un-necessesary scraping
Paul McInnis 2020
"""

from collections import namedtuple
from copy import deepcopy
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple

import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobfunnel.backend import Job
from jobfunnel.backend.tools import Logger
from jobfunnel.resources import (
    DEFAULT_MAX_TFIDF_SIMILARITY,
    MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH,
    DuplicateType,
    Remoteness,
)

DuplicatedJob = namedtuple(
    "DuplicatedJob",
    ["original", "duplicate", "type"],
)


class JobFilter(Logger):
    """Class Used by JobFunnel and BaseScraper to filter collections of jobs

    TODO: make more configurable, maybe with a FilterBank class.
    """

    def __init__(
        self,
        user_block_jobs_dict: Optional[Dict[str, str]] = None,
        duplicate_jobs_dict: Optional[Dict[str, str]] = None,
        blocked_company_names_list: Optional[List[str]] = None,
        max_job_date: Optional[datetime] = None,
        max_similarity: float = DEFAULT_MAX_TFIDF_SIMILARITY,
        desired_remoteness: Remoteness = Remoteness.ANY,
        min_tfidf_corpus_size: int = MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH,
        log_level: int = logging.INFO,
        log_file: str = None,
    ) -> None:
        """Init

        TODO: need a config for this

        Args:
            user_block_jobs_dict (Optional[Dict[str, str]], optional): dict
                containing user's blocked jobs. Defaults to None.
            duplicate_jobs_dict (Optional[Dict[str, str]], optional): dict
                containing duplicate jobs, detected by content. Defaults to None
            blocked_company_names_list (Optional[List[str]], optional): list of
                company names disallowed from results. Defaults to None.
            max_job_date (Optional[datetime], optional): maximium date that a
                job can be scraped. Defaults to None.
            desired_remoteness (Remoteness, optional): The desired level of
                work-remoteness. ANY will impart no restriction.
            log_level (Optional[int], optional): log level. Defaults to INFO.
            log_file (Optional[str], optional): log file, Defaults to None.
        """
        super().__init__(
            level=log_level,
            file_path=log_file,
        )
        self.user_block_jobs_dict = user_block_jobs_dict or {}
        self.duplicate_jobs_dict = duplicate_jobs_dict or {}
        self.blocked_company_names_list = blocked_company_names_list or []
        self.max_job_date = max_job_date
        self.max_similarity = max_similarity
        self.desired_remoteness = desired_remoteness
        self.min_tfidf_corpus_size = min_tfidf_corpus_size

        # Retrieve stopwords if not already downloaded
        try:
            stopwords = nltk.corpus.stopwords.words("english")
        except LookupError:
            nltk.download("stopwords", quiet=True)
            stopwords = nltk.corpus.stopwords.words("english")

        # Init vectorizer
        self.vectorizer = TfidfVectorizer(
            strip_accents="unicode",
            lowercase=True,
            analyzer="word",
            stop_words=stopwords,
        )

    def filter(
        self, jobs_dict: Dict[str, Job], remove_existing_duplicate_keys: bool = True
    ) -> Dict[str, Job]:
        """Filter jobs that fail numerous tests, possibly including duplication

        Arguments:
            remove_existing_duplicate_keys: pass True to remove jobs if their
                ID was previously detected to be a duplicate via TFIDF cosine
                similarity

        NOTE: if you remove duplicates before processesing them into updates
              you will retain potentially stale job information.

        Returns:
            jobs_dict with all filtered items removed.
        """
        return {
            key_id: job
            for key_id, job in jobs_dict.items()
            if not self.filterable(
                job, check_existing_duplicates=remove_existing_duplicate_keys
            )
        }

    def filterable(self, job: Job, check_existing_duplicates: bool = True) -> bool:
        """Filter jobs out using all our available filters

        NOTE: this allows job to be partially initialized
        NOTE: if a job has UNKNOWN remoteness, we will include it anyways
        TODO: we should probably add some logging to this?

        Arguments:
            check_existing_duplicates: pass True to check if ID was previously
                detected to be a duplicate via TFIDF cosine similarity

        Returns:
            True if the job should be removed from incoming data, else False
        """
        return bool(
            job.status
            and job.is_remove_status
            or (job.company in self.blocked_company_names_list)
            or (job.post_date and self.max_job_date and job.is_old(self.max_job_date))
            or (
                job.key_id
                and self.user_block_jobs_dict
                and job.key_id in self.user_block_jobs_dict
            )
            or (check_existing_duplicates and self.is_duplicate(job))
            or (
                job.remoteness != Remoteness.UNKNOWN
                and self.desired_remoteness != Remoteness.ANY
                and job.remoteness != self.desired_remoteness
            )
        )

    def is_duplicate(self, job: Job) -> bool:
        """Return true if passed Job has key_id and it is in our duplicates list"""
        return bool(
            job.key_id
            and self.duplicate_jobs_dict
            and job.key_id in self.duplicate_jobs_dict
        )

    def find_duplicates(
        self,
        existing_jobs_dict: Dict[str, Job],
        incoming_jobs_dict: Dict[str, Job],
    ) -> List[DuplicatedJob]:
        """Remove all known duplicates from jobs_dict and update original data

        TODO: find duplicates by content within existing jobs

        Args:
            existing_jobs_dict (Dict[str, Job]): dict of jobs keyed by key_id.
            incoming_jobs_dict (Dict[str, Job]): dict of new jobs by key_id.

        Returns:
            Dict[str, Job]: jobs dict with all jobs keyed by known-duplicate
                key_ids removed, and their originals updated.
        """
        duplicate_jobs_list = []  # type: List[DuplicatedJob]
        filt_existing_jobs_dict = deepcopy(existing_jobs_dict)
        filt_incoming_jobs_dict = {}  # type: Dict[str, Job]

        # Look for matches by key id only
        for key_id, incoming_job in incoming_jobs_dict.items():
            # The key-ids are a direct match between existing and new
            if key_id in existing_jobs_dict:
                self.logger.debug(
                    f"Identified duplicate {key_id} between incoming data "
                    "and existing data."
                )
                duplicate_jobs_list.append(
                    DuplicatedJob(
                        original=existing_jobs_dict[key_id],
                        duplicate=incoming_job,
                        type=DuplicateType.KEY_ID,
                    )
                )

            # The key id is a known-duplicate we detected via content match
            # NOTE: original and duplicate have the same key id.
            elif key_id in self.duplicate_jobs_dict:
                self.logger.debug(
                    f"Identified existing content-matched duplicate {key_id} "
                    "in incoming data."
                )
                duplicate_jobs_list.append(
                    DuplicatedJob(
                        original=None,  # TODO: load ref from duplicates dict
                        duplicate=incoming_job,
                        type=DuplicateType.EXISTING_TFIDF,
                    )
                )
            else:
                # This key_id is not duplicate, we can use it for TFIDF
                filt_incoming_jobs_dict[key_id] = deepcopy(incoming_job)

        # Run the tfidf vectorizer if we have enough jobs left after removing
        # key duplicates
        if (
            len(filt_incoming_jobs_dict.keys()) + len(filt_existing_jobs_dict.keys())
            < self.min_tfidf_corpus_size
        ):
            self.logger.warning(
                "Skipping content-similarity filter because there are fewer than "
                f"{self.min_tfidf_corpus_size} jobs."
            )
        elif filt_incoming_jobs_dict:
            duplicate_jobs_list.extend(
                self.tfidf_filter(
                    incoming_jobs_dict=filt_incoming_jobs_dict,
                    existing_jobs_dict=filt_existing_jobs_dict,
                )
            )
        else:
            self.logger.warning(
                "Skipping content-similarity filter because there are no "
                "incoming jobs"
            )

        # Update duplicates list with more JSON-friendly entries
        # TODO: we should retain a reference to the original job's contents
        self.duplicate_jobs_dict.update(
            {j.duplicate.key_id: j.duplicate.as_json_entry for j in duplicate_jobs_list}
        )

        return duplicate_jobs_list

    def tfidf_filter(
        self,
        incoming_jobs_dict: Dict[str, dict],
        existing_jobs_dict: Dict[str, dict],
    ) -> List[DuplicatedJob]:
        """Fit a tfidf vectorizer to a corpus of Job.DESCRIPTIONs and identify
        duplicate jobs by cosine-similarity.

        NOTE/WARNING: if you are running this method, you should have already
            removed any duplicates by key_id
        NOTE: this only uses job descriptions to do the content matching.
        NOTE: it is recommended that you have at least around 25 ish Jobs.
        TODO: need to handle existing_jobs_dict = None
        TODO: have this raise an exception if there are too few words.
        TODO: we should consider caching the transformed corpus.

        Args:
            incoming_jobs_dict (Dict[str, dict]): dict of jobs containing
                potential duplicates (i.e jobs we just scraped)
            existing_jobs_dict (Dict[str, dict]): the existing jobs dict
                (i.e. Master CSV)

        Raises:
            ValueError: incoming_jobs_dict contains no job descriptions

        Returns:
            List[DuplicatedJob]: list of new duplicate Jobs and their existing
                Jobs found via content matching (for use in JobFunnel).
        """

        def __dict_to_ids_and_words(
            jobs_dict: Dict[str, Job],
            is_incoming: bool = False,
        ) -> Tuple[List[str], List[str]]:
            """Get query words and ids as lists + prefilter
            NOTE: this is just a convenience method since we do this 2x
            TODO: consider moving this once/if we change iteration
            """
            ids = []  # type: List[str]
            words = []  # type: List[str]
            filt_job_dict = {}  # type: Dict[str, Job]
            for job in jobs_dict.values():
                if is_incoming and job.key_id in self.duplicate_jobs_dict:
                    # NOTE: we should never see this for incoming jobs.
                    # we will see it for existing jobs since duplicates can
                    # share a key_id.
                    raise ValueError(
                        "Attempting to run TFIDF with existing duplicate "
                        f"{job.key_id}"
                    )
                elif not len(job.description):
                    self.logger.debug(
                        f"Removing {job.key_id} from scrape result, empty "
                        "description."
                    )
                else:
                    ids.append(job.key_id)
                    words.append(job.description)
                    # NOTE: We want to leave changing incoming_jobs_dict in
                    # place till the end or we will break usage of
                    # Job.update_if_newer()
                    filt_job_dict[job.key_id] = job

            # TODO: assert on length of contents of the lists as well
            if not words:
                raise ValueError("No data to fit, are your job descriptions all empty?")
            return ids, words, filt_job_dict

        query_ids, query_words, filt_incoming_jobs_dict = __dict_to_ids_and_words(
            incoming_jobs_dict, is_incoming=True
        )

        # Calculate corpus and format query data for TFIDF calculation
        corpus = []  # type: List[str]
        if existing_jobs_dict:
            self.logger.debug("Running TFIDF on incoming vs existing data.")
            (
                reference_ids,
                reference_words,
                filt_existing_jobs_dict,
            ) = __dict_to_ids_and_words(existing_jobs_dict, is_incoming=False)
            corpus = query_words + reference_words
        else:
            self.logger.debug("Running TFIDF on incoming data only.")
            reference_ids = (query_ids,)
            reference_words = query_words
            filt_existing_jobs_dict = filt_incoming_jobs_dict
            corpus = query_words

        # Provide a warning if we have few words.
        # TODO: warning should reflect actual corpus size
        if len(corpus) < self.min_tfidf_corpus_size:
            self.logger.warning(
                "It is not recommended to use this filter with less than "
                f"{self.min_tfidf_corpus_size} jobs"
            )

        # Fit vectorizer to entire corpus
        self.vectorizer.fit(corpus)

        # Calculate cosine similarity between reference and current blurbs
        # This is a list of the similarity between that query job and all the
        # TODO: impl. in a more efficient way since fit() does the transform too
        similarities_per_query = cosine_similarity(
            self.vectorizer.transform(query_words),
            self.vectorizer.transform(reference_words) if existing_jobs_dict else None,
        )

        # Find Duplicate jobs by similarity score
        # NOTE: multiple jobs can be determined to be a duplicate of same job!
        # TODO: traverse this so we look at max similarity for original vs query
        # currently it's the other way around so we can look at multi-matching
        # original jobs but not multiple matching queries for our original job.
        new_duplicate_jobs_list = []  # type: List[DuplicatedJob]
        for query_similarities, query_id in zip(similarities_per_query, query_ids):
            # Identify the jobs in existing_jobs_dict that our query is a
            # duplicate of
            # TODO: handle if everything is highly similar!
            similar_indeces = np.where(query_similarities >= self.max_similarity)[0]
            if similar_indeces.size > 0:
                # TODO: capture if more jobs are similar by content match
                top_similar_job = np.argmax(query_similarities[similar_indeces])
                self.logger.debug(
                    f"Identified incoming job {query_id} as new duplicate by "
                    "contents of existing job "
                    f"{reference_ids[top_similar_job]}"
                )
                new_duplicate_jobs_list.append(
                    DuplicatedJob(
                        original=filt_existing_jobs_dict[
                            reference_ids[top_similar_job]
                        ],
                        duplicate=filt_incoming_jobs_dict[query_id],
                        type=DuplicateType.NEW_TFIDF,
                    )
                )

        if not new_duplicate_jobs_list:
            self.logger.debug("Found no duplicates by content-matching.")

        # returns a list of newly-detected duplicate Jobs
        return new_duplicate_jobs_list
