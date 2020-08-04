"""Filters that are used in jobfunnel's filter() method or as intermediate
filters to reduce un-necessesary scraping
"""
import nltk
import logging
from datetime import datetime, date, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Optional
from numpy import delete as np_delete, max as np_max, fill_diagonal

from jobfunnel.backend import Job


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
                 max_similarity: float = 0.75):
    """ Fit a tfidf vectorizer to a corpus of all listing's text.

        Args:
            cur_dict: today's job scrape dict
            prev_dict: the existing master list job dict
            max_similarity: threshold above which blurb similarity = duplicate

        Returns:
            list of duplicate job ids which were removed from cur_dict
    """
    # retrieve stopwords if not already downloaded
    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')

    # init vectorizer
    vectorizer = TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                 analyzer='word', stop_words=stopwords)

    # init list to store duplicate ids
    duplicate_ids = {}

    if prev_dict is None:
        # get query words and ids as lists
        query_ids = [job.key_id for job in cur_dict.values()]
        query_words = [job.description for job in cur_dict.values()]

        # returns cosine similarity between jobs as square matrix (n,n)
        similarities = cosine_similarity(vectorizer.fit_transform(query_words))
        # fills diagonals with 0, so whole dict does not get popped
        fill_diagonal(similarities, 0)
        # init index
        index = 0
        # identifies duplicates and stores them in duplicate ids dictionary
        while True:
            # loop breaks when index is equal to matrix height
            if index == len(similarities):
                break

            # deletes row and column, every time a max is found for a job id
            if np_max(similarities[index]) >= max_similarity:
                # query ids are popped so index always matches correct element
                duplicate_ids.update(
                    {query_ids[index]: cur_dict.pop(query_ids.pop(index))})
                # reduce matrix dimensions, (n-1, n-1)
                similarities = np_delete(similarities, index, axis=0)
                similarities = np_delete(similarities, index, axis=1)

            else:  # increment index by one
                index += 1
        # log something
        logging.info(f'Found and removed {len(duplicate_ids.keys())} '
                     f're-posts/duplicates via TFIDF cosine similarity!')

    else:
        # checks current scrape for re-posts/duplicates
        duplicate_ids = tfidf_filter(cur_dict)

        # get query words and ids as lists
        query_ids = [job.key_id for job in cur_dict.values()]
        query_words = [job.description for job in cur_dict.values()]

        # get reference words as list
        reference_words = [job.description for job in prev_dict.values()]

        # fit vectorizer to entire corpus
        vectorizer.fit(query_words + reference_words)

        # set reference tfidf for cosine similarity later
        references = vectorizer.transform(reference_words)

        # calculate cosine similarity between reference and current blurbs
        similarities = cosine_similarity(
            vectorizer.transform(query_words), references)

        # get duplicate job ids and pop them
        for sim, query_id in zip(similarities, query_ids):
            if np_max(sim) >= max_similarity:
                duplicate_ids.update({query_id: cur_dict.pop(query_id)})

        # log something
        logging.info(
            f'Found {len(cur_dict.keys())} unique listings and '
            f'{len(duplicate_ids.keys())} duplicates '
            f'via TFIDF cosine similarity'
        )

    # returns a dictionary of duplicate key_ids
    return duplicate_ids
