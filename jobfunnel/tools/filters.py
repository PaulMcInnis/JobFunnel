from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Optional
import nltk
import numpy as np
import logging


# Filter duplicate job ids.
def id_filter(cur_dict: Dict[str, dict], prev_dict: Dict[str, dict], provider):
    """ Filter duplicates on job-id per provider
        Args:
            cur_dict: today's job scrape dict
            prev_dict: the existing master list job dict
            provider: job board used

    """
    # Get job_ids from scrape and master list by provider as lists
    cur_job_ids = [job['id'] for job in cur_dict.values()]
    prev_job_ids = [job['id'] for job in prev_dict.values()
                    if job['provider'] == provider]

    # get duplicate job ids and pop them from current scrape
    duplicate_ids = []
    for job_id in cur_job_ids:
        if job_id in prev_job_ids:
            duplicate_ids.append(cur_dict.pop(job_id)['id'])

    # log duplicate id's
    logging.info("found {} unique job ids and {} duplicates "
                 "from {}".format(len(cur_dict.keys()), len(duplicate_ids),
                                  provider))


def tfidf_filter(cur_dict: Dict[str, dict],
                 prev_dict: Optional[Dict[str, dict]] = None,
                 max_similarity: float = 0.75):
    """ Fit a TFIDF vectorizer to a corpus of all listing's text

        Args:
            cur_dict: today's job scrape dict
            prev_dict: the existing master list job dict
            max_similarity: threshold above which a blurb similarity =
            duplicate

        Returns:
            list of duplicate job ids which were removed from cur_dict
    """
    # Retrieve stopwords
    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        try:
            nltk.download('stopwords', quiet=True)
        except e:
            print(e)

    # init vectorizer
    vectorizer = TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                 analyzer='word', stop_words=stopwords)
    # init list to store duplicate ids:
    duplicate_ids = []

    if prev_dict is None:
        # get query words and ids as lists
        query_ids = [job['id'] for job in cur_dict.values()]
        query_words = [job['blurb'] for job in cur_dict.values()]

        # Returns cosine similarity between jobs in cur_dict as square matrix
        similarities = cosine_similarity(vectorizer.fit_transform(query_words))

        # Fills diagonals with 0, so whole dict does not get popped
        np.fill_diagonal(similarities, 0)
        # Deletes row and column every time a max is identified for a job id.
        # with dimensions defined as (n-1, n-1)
        index = 0  # init index
        while True:
            # Loop breaks when index is larger than matrix height
            if index == len(similarities):
                break
            # Gets duplicate id and reduces cosine similarity matrix
            if np.max(similarities[index]) >= max_similarity:
                duplicate_ids.append(cur_dict.pop(query_ids.pop(index))['id'])
                similarities = np.delete(similarities, index, axis=0)
                similarities = np.delete(similarities, index, axis=1)
            else:  # Increments index by one, if current gets no results
                index += 1
        # log something
        logging.info("Found and removed {} re-posts/duplicates "
                     "via TFIDF cosine similarity".len(duplicate_ids))

    else:
        # Checks cur_dict for re-posts/duplicates
        duplicate_ids.extend(tfidf_filter(cur_dict))

        # get query words and ids as lists
        query_ids = [job['id'] for job in cur_dict.values()]
        query_words = [job['blurb'] for job in cur_dict.values()]

        # get reference words as list
        reference_words = [job['blurb'] for job in prev_dict.values()]

        # fit vectorizer to entire corpus
        vectorizer.fit(query_words + reference_words)

        # set reference tfidf for cosine similarity later
        references = vectorizer.transform(reference_words)

        # calculate cosine similarity between reference and current blurbs
        similarities = cosine_similarity(
            vectorizer.transform(query_words), references)

        # get duplicate job ids and pop them
        for sim, query_id in zip(similarities, query_ids):
            if np.max(sim) >= max_similarity:
                duplicate_ids.append(cur_dict.pop(query_id)['id'])

        # log something
        logging.info("found {} unique listings and {} duplicate listings "
                     "via TFIDF cosine similarity".format(len(cur_dict.keys()),
                                                      len(duplicate_ids)))

    return duplicate_ids
