from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from typing import List, Dict
import os
import numpy as np
import pickle
import string
import logging


# Filter duplicate job ids.
def id_filter(cur_dict: Dict[str, dict], prev_dict: Dict[str, dict], provider):
    """function that filters duplicates based on job-id per site"""
    # Get job_ids from scrape and master list by provider as lists
    cur_job_ids, prev_job_ids = [], []
    for job in cur_dict.values():
        cur_job_ids.append(job['id'])

    for job in prev_dict.values():
        if job['provider'] == provider:
            prev_job_ids.append(job['id'])

    # get duplicate job ids and pop them from current scrape
    duplicate_ids = []
    for job_id in cur_job_ids:
        if job_id in prev_job_ids:
            duplicate_ids.append(cur_dict.pop(job_id)['id'])

    # log duplicate id's
    logging.info("found {} unique job ids and {} duplicates "
                 "from {}".format(len(cur_dict.keys()), len(duplicate_ids),
                                  provider))


def tfidf_filter(cur_dict: Dict[str, dict], prev_dict: Dict[str, dict],
                 max_similarity: float = 0.75):
    """ Fit a TFIDF vectorizer to a corpus of all listing's text

        Args:
            cur_dict: the existing masterlist job dict
            prev_dict: today's job scrape dict
            max_similarity: threshold above which a blurb similarity =
            duplicate

        Returns:
            list of duplicate job ids which were removed from cur_dict

        @TODO skip calculating metric for jobs which have the same job id!
    """
    # init vectorizer
    vectorizer = TfidfVectorizer(strip_accents='unicode',
                                 lowercase=True,
                                 analyzer='word')
    # get reference words as list
    reference_words = [job['blurb'] for job in prev_dict.values()]

    # get query words as list
    query_words, query_ids = [], []
    for job in cur_dict.values():
        query_words.append(job['blurb'])
        query_ids.append(job['id'])

    # fit vectorizer to entire corpus
    vectorizer.fit(query_words + reference_words)

    # set reference tfidf for cosine similarity later
    references = vectorizer.transform(reference_words)

    # calculate cosine similarity between reference and current blurbs
    similarities = cosine_similarity(
        vectorizer.transform(query_words), references)

    # get duplicate job ids and pop them
    duplicate_ids = []
    for sim, query_id in zip(similarities, query_ids):
        if np.max(sim) >= max_similarity:
            duplicate_ids.append(cur_dict.pop(query_id)['id'])

    # log something
    logging.info("found {} unique listings and {} duplicate listings "
                 "via TFIDF cosine similarity".format(len(cur_dict.keys()),
                                                      len(duplicate_ids)))
    return duplicate_ids
