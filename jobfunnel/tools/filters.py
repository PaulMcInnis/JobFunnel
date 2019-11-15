from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from typing import List, Dict
import os
import numpy as np
import pickle
import string
import logging


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
