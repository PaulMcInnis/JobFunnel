from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from typing import List, Dict
import os
import numpy as np
import pickle
import string
import logging

class TextVectorizer(object):
    """ Class to fit a TFIDF vectorizer
        @ TODO move into a seperate file
    """

    def __init__(self, corpus: List[str]):
        """ Init TFIDF vectorizer, only works for English"""
        self.vectorizer = TfidfVectorizer(strip_accents='unicode',
                                          lowercase=True,
                                          analyzer='word')
        if corpus:
            self.set_corupus(corpus)

    def set_corupus(self, corpus: List[str]):
        """ Fit vectorizer to all words in entire corpus"""
        self.vectorizer.fit(corpus)

    def set_reference_words(self, reference_words: List[str]):
        """ Set the reference for calculating similarity"""
        self.references = self.vectorizer.transform(reference_words)

    def get_cosine_similarity(self, words: List[str], identifiers: List[str]):
        """ Get similarity (per reference item) between a list of words and
            and return scores with identifiers

            Returns:
                { id (str): similarity_scores (List[float]) }
        """

        # calculate cosine similarity between reference and current blurbs
        return dict(zip(identifiers,
                        cosine_similarity(self.vectorizer.transform(words),
                                          self.references)[:,0]))


def similarity_filter(cur_dict: Dict[str, dict], prev_dict: Dict[str, dict],
                      max_similarity: float = 0.75):
    """ Fit a TFIDF vectorizer to a corpus of all listing's text

        Args:
            cur_dict: the existing masterlist job dict
            prev_dict: today's job scrape dict
            max_similarity: threshold above which a blurb similarity = duplicate

        Returns:
            list of duplicate job ids which were removed from cur_dict

        @TODO skip calculating metric for jobs which have the same job id!
    """
    # build corpus
    query_words = [job['blurb'] for job in cur_dict.values()]
    reference_words = [job['blurb'] for job in prev_dict.values()]

    # init a text vectorizer
    vectorizer = TextVectorizer(query_words + reference_words)
    vectorizer.set_reference_words(reference_words)

    # calculate similarities
    query_text, ids = [], []
    for job in cur_dict.values():
        query_text.append(job['blurb'])
        ids.append(job['id'])
    similarities = vectorizer.get_cosine_similarity(query_text, identifiers=ids)

    # get duplicate job ids and pop them
    duplicate_ids = []
    for query_id, sim in similarities.items():
        if np.max(sim) >= max_similarity:
            duplicate_ids.append(cur_dict.pop(query_id)['id'])

    # log something
    logging.info("found {} unique listings and {} duplicate listings "
                 "via TFIDF cosine similarity".format(len(cur_dict.keys()),
                                                      len(duplicate_ids)))
    return duplicate_ids

