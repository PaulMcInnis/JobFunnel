"""Filters that are used in jobfunnel's filter() method or as intermediate
filters to reduce un-necessesary scraping.
FIXME: we should have a Enum(Filter) for all job filters to allow configuration
and generic log messages.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import os

import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobfunnel.backend import Job
from jobfunnel.backend.tools import update_job_if_newer, get_logger
from jobfunnel.resources import (
    DEFAULT_MAX_TFIDF_SIMILARITY, MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH
)


class JobFilter:
    """Class Used by JobFunnel and BaseScraper to filter collections of jobs
    """
    def __init__(self, user_block_jobs_dict: Optional[Dict[str, str]] = None,
                 duplicate_jobs_dict: Optional[Dict[str, str]] = None,
                 blocked_company_names_list: Optional[List[str]] = None,
                 max_job_date: Optional[datetime] = None) -> None:
        """Init

        NOTE: remember to update attributes as needed.

        Args:
            user_block_jobs_dict (Optional[Dict[str, str]], optional): dict
                containing user's blocked jobs. Defaults to None.
            duplicate_jobs_dict (Optional[Dict[str, str]], optional): dict
                containing duplicate jobs, detected by content. Defaults to None
            blocked_company_names_list (Optional[List[str]], optional): list of
                company names disallowed from results. Defaults to None.
            max_job_date (Optional[datetime], optional): maximium date that a
                job can be scraped. Defaults to None.
        """
        self.user_block_jobs_dict = user_block_jobs_dict or {}
        self.duplicate_jobs_dict = duplicate_jobs_dict or {}
        self.blocked_company_names_list = blocked_company_names_list or []
        self.max_job_date = max_job_date
        # TODO: add tfidf to this class for per-job scraping

    def filter(self, job: Job) -> bool:
        """Filter jobs out using all our available filters
        TODO: arrange checks by how long they take to run
        NOTE: this does a lot of checks because job may be partially initialized
        """
        return (
            job.status and job.is_remove_status
            or (job.company in self.blocked_company_names_list)
            or (job.post_date and self.max_job_date
                and job.is_old(self.max_job_date))
            or (job.key_id and self.user_block_jobs_dict
                and job.key_id in self.user_block_jobs_dict)
            or (job.key_id and self.duplicate_jobs_dict
                and job.key_id in self.duplicate_jobs_dict)
        )


def tfidf_filter(cur_dict: Dict[str, dict],
                 prev_dict: Optional[Dict[str, dict]] = None,
                 max_similarity: float = DEFAULT_MAX_TFIDF_SIMILARITY,
                 duplicate_jobs_dict: Optional[Dict[str, str]] = None,
                 log_level: int = logging.INFO,
                 log_file: str = None,
                 ) -> List[Job]:
    """Fit a tfidf vectorizer to a corpus of Job.DESCRIPTIONs and identify
    duplicate jobs by cosine-similarity.

    NOTE: This will update jobs in cur_dict if the content match has a newer
        post_date.
    NOTE/WARNING: if you are running this method, you should have already
        removed any duplicates by key_id
    FIXME: we should make max_similarity configurable in SearchConfig
    FIXME: this should be integrated into JobFilter (on the fly content match)
    NOTE: this only uses job descriptions to do the content matching.
    NOTE: it is recommended that you have at least around 25 ish Jobs.
    TODO: have this raise an exception if there are too few words?
    FIXME: make this a class so we can call it many times on single queries.

    Args:
        cur_dict (Dict[str, dict]): dict of jobs containing potential duplicates
             (i.e jobs we just scraped)
        prev_dict (Optional[Dict[str, dict]], optional): the existing jobs dict
            (i.e. master CSV contents). If None, we will remove duplicates
            from within the cur_dict only. Defaults to None.
        max_similarity (float, optional): threshold above which blurb similarity
            is considered a duplicate. Defaults to DEFAULT_MAX_TFIDF_SIMILARITY.
        duplicate_jobs_dict (str, optional): cntents of user's duplicate job
            detection JSON so we can make content matching persist better.
        ...

    Raises:
        ValueError: cur_dict contains no job descriptions

    Returns:
        List[Job]: list of new duplicate Jobs which were removed from cur_dict
    """
    logger = get_logger(
        tfidf_filter.__name__,
        log_level,
        log_file,
        f"[%(asctime)s] [%(levelname)s] {tfidf_filter.__name__}: %(message)s"
    )

    # Retrieve stopwords if not already downloaded
    # TODO: we should use this to make jobs attrs tokenizable as a property.
    # TODO: make the vectorizer persistant.
    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')

    # init vectorizer NOTE: pretty fast call but we should do this once!
    vectorizer = TfidfVectorizer(
        strip_accents='unicode',
        lowercase=True,
        analyzer='word',
        stop_words=stopwords,
    )

    # Load known duplicate keys from JSON if we have it
    # NOTE: this allows us to do smaller TFIDF comparisons because we ensure
    # that we are skipping previously-detected job duplicates (by id)
    duplicate_jobs_dict = duplicate_jobs_dict or {}  # type: Dict[str, str]
    if duplicate_jobs_dict:
        existing_duplicate_keys = duplicate_jobs_dict.keys()
    else:
        existing_duplicate_keys = {}  # type: Dict[str, str]

    def __dict_to_ids_and_words(jobs_dict: Dict[str, Job]
                                ) -> Tuple[List[str], List[str]]:
        """Get query words and ids as lists + prefilter
        NOTE: this is just a convenience method since we do this 2x
        """
        ids = []  # type: List[str]
        words = []  # type: List[str]
        filt_job_dict = {}  # type: Dict[str, Job]
        for job in cur_dict.values():
            if job.key_id in existing_duplicate_keys:
                logger.debug(
                    f"Removing {job.key_id} from scrape result, existing "
                    "duplicate."
                )
            elif not len(job.description):
                logger.debug(
                    f"Removing {job.key_id} from scrape result, empty "
                    "description."
                )
            else:
                ids.append(job.key_id)
                words.append(job.description)
                # NOTE: We want to leave changing cur_dict in place till the end
                # or we will break usage of update_job_if_newer()
                filt_job_dict[job.key_id] = job

        # TODO: assert on length of contents of the lists as well
        if not words:
            raise ValueError(
                "No data to fit, are your job descriptions all empty?"
            )
        return ids, words, filt_job_dict

    query_ids, query_words, filt_cur_dict = __dict_to_ids_and_words(cur_dict)
    reference_ids, reference_words, filt_prev_dict = __dict_to_ids_and_words(
        prev_dict
    )

    # Provide a warning if we have few words.
    corpus = query_words + reference_words
    if len(corpus) < MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH:
        logger.warning(
            "It is not recommended to use this filter with less than "
            f"{MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH} words"
        )

    # Fit vectorizer to entire corpus
    vectorizer.fit(corpus)

    # Calculate cosine similarity between reference and current blurbs
    # This is a list of the similarity between that query job and all the
    # TODO: impl. in a more efficient way since fit() does the transform already
    similarities_per_query = cosine_similarity(
        vectorizer.transform(query_words),
        vectorizer.transform(reference_words),
    )

    # Get duplicate job ids and pop them, updating cur_dict if they are newer
    # NOTE: multiple jobs can be determined to be a duplicate of the same job!
    new_duplicate_jobs_list = []  # type: List[Job]
    for query_similarities, query_id in zip(similarities_per_query, query_ids):

        # Identify the jobs in prev_dict that our query is a duplicate of
        # FIXME: handle if everything is highly similar!
        for similar_index in np.where(query_similarities >= max_similarity)[0]:
            update_job_if_newer(
                filt_prev_dict[reference_ids[similar_index]],
                filt_cur_dict[query_id],
            )
            new_duplicate_jobs_list.append(filt_cur_dict[query_id])

    # Make sure the duplicate jobs list contains only unique entries
    new_duplicate_jobs_list = list(set(new_duplicate_jobs_list))

    # Pop duplicates from cur_dict and return them
    # NOTE: we cannot change cur_dict in above loop, or no updates possible.
    if new_duplicate_jobs_list:
        for job in new_duplicate_jobs_list:
            cur_dict.pop(job.key_id)
            logger.debug(
                f"Removed {job.key_id} from scraped data, TFIDF content match."
            )

        logger.info(
            f'Found and removed {len(new_duplicate_jobs_list)} '
            f're-posts/duplicate postings via TFIDF cosine similarity.'
        )

    # returns a list of newly-detected duplicate Jobs
    return new_duplicate_jobs_list
