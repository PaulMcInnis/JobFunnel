"""Filters that are used in jobfunnel's filter() method or as intermediate
filters to reduce un-necessesary scraping.
FIXME: we should have a Enum(Filter) for all job filters to allow configuration
and generic log messages.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import json

import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobfunnel.backend import Job
from jobfunnel.backend.tools import update_job_if_newer, get_logger
from jobfunnel.resources import DEFAULT_MAX_TFIDF_SIMILARITY


T_NOW = datetime.now()


def job_is_old(job: Job, number_of_days: int) -> bool:
    """Identify if a job is older than number_of_days from today

    NOTE: modifies job_dict in-place

        Args:
            job_dict: today's job scrape dict
            number_of_days: how many days old a job can be

        Returns:
            True if it's older than number of days
            False if it's fresh enough to keep
    """
    assert number_of_days > 0
    # Calculate the oldest date a job can be
    # NOTE: we may want to just set job.status = JobStatus.OLD
    return job.post_date < (T_NOW - timedelta(days=number_of_days))


def tfidf_filter(cur_dict: Dict[str, dict],
                 prev_dict: Optional[Dict[str, dict]] = None,
                 max_similarity: float = DEFAULT_MAX_TFIDF_SIMILARITY,
                 duplicate_jobs_file: Optional[str] = None,
                 log_level: int = logging.INFO,
                 log_file: str = None,
                 ) -> List[Job]:
    """Fit a tfidf vectorizer to a corpus of Job.DESCRIPTIONs and identify
    duplicate jobs by cosine-similarity.

    NOTE: This will update jobs in cur_dict if the content match has a newer
        post_date.
    FIXME: we should make max_similarity configurable in SearchConfig
    FIXME: this should be integrated into jobfunnel.filter with other filters
    FIXME: fix logger arg-passing once we get this in some kind of class
    NOTE: this only uses job descriptions to do the content matching.
    NOTE: it is recommended that you have at least around 25 Jobs.
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
        duplicate_jobs_file (str, optional): location to save duplicates that
            we identify via content matching. Defaults to None.
        ...

    Raises:
        ValueError: cur_dict contains no job descriptions

    Returns:
        List[Job]: list of duplicate Jobs which were removed from cur_dict
    """
    logger = get_logger(
        tfidf_filter.__name__,
        log_level,
        log_file,
        f"[%(asctime)s] [%(levelname)s] {tfidf_filter.__name__}: %(message)s"
    )

    # Retrieve stopwords if not already downloaded
    # TODO: we should use this to make jobs attrs tokenizable as a property.
    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')

    # init vectorizer
    vectorizer = TfidfVectorizer(
        strip_accents='unicode',
        lowercase=True,
        analyzer='word',
        stop_words=stopwords,
    )

    # TODO: assert on length of contents of the lists + combine into one method
    # Get query words and ids as lists for convenience
    query_ids = []  # type: List[str]
    query_words = []  # type: List[str]
    for job in cur_dict.values():
        if len(job.description) > 0:
            query_ids.append(job.key_id)
            query_words.append(job.description)

    if not query_words:
        raise ValueError("No data to fit, are your job descriptions all empty?")

    # Get reference words as list
    reference_ids = []  # type: List[str]
    reference_words = []  # type: List[str]
    for job in prev_dict.values():
        if len(job.description) > 0:
            reference_ids.append(job.key_id)
            reference_words.append(job.description)

    if not reference_words:
        raise ValueError("No data to fit, are your job descriptions all empty?")

    # Fit vectorizer to entire corpus
    vectorizer.fit(query_words + reference_words)

    # Calculate cosine similarity between reference and current blurbs
    # This is a list of the similarity between that query job and all the
    # TODO: impl. in a more efficient way since fit() does the transform already
    similarities_per_query = cosine_similarity(
        vectorizer.transform(query_words),
        vectorizer.transform(reference_words),
    )

    # Get duplicate job ids and pop them, updating cur_dict if they are newer
    duplicate_jobs_list = []  # type: List[Job]
    for query_similarities, query_id in zip(similarities_per_query, query_ids):

        # Identify the jobs in prev_dict that our query is a duplicate of
        # FIXME: handle if everything is highly similar!
        for similar_index in np.where(query_similarities >= max_similarity)[0]:
            update_job_if_newer(
                prev_dict[reference_ids[similar_index]],
                cur_dict[query_id],
            )
            duplicate_jobs_list.append(cur_dict.pop(query_id))
            logger.debug(
                f"Removed {query_id} from scraped data, TFIDF content match."
            )

    # Save to our duplicates file if any are detected exist
    if duplicate_jobs_list:

        logger.info(
            f'Found and removed {len(duplicate_jobs_list)} '
            f're-posts/duplicate postings via TFIDF cosine similarity.'
        )

        # NOTE: we use indent=4 so that it stays human-readable.
        if duplicate_jobs_file:
            with open(duplicate_jobs_file, 'w', encoding='utf8') as outfile:
                outfile.write(
                    json.dumps(
                        {dj.key_id: dj.as_json_entry
                         for dj in duplicate_jobs_list},
                        indent=4,
                        sort_keys=True,
                        separators=(',', ': '),
                        ensure_ascii=False,
                    )
                )
        else:
            logger.warning(
                "Duplicates will not be saved, no duplicates list file set. "
                "Saving to a duplicates file will ensure that these persist."
            )

    # returns a list of duplicate Jobs
    return duplicate_jobs_list
