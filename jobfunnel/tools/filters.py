#import nltk
import logging

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Optional
from numpy import delete as np_delete, max as np_max, fill_diagonal


def id_filter(cur_dict: Dict[str, dict], prev_dict: Dict[str, dict], provider):
    """ Filter duplicates on job id per provider.

        Args:
            cur_dict: today's job scrape dict
            prev_dict: the existing master list job dict
            provider: job board used

    """
    # get job ids from scrape and master list by provider as lists
    cur_job_ids = [job['id'] for job in cur_dict.values()]
    prev_job_ids = [job['id'] for job in prev_dict.values()
                    if job['provider'] == provider]

    # pop duplicate job ids from current scrape
    duplicate_ids = [cur_dict.pop(job_id)['id'] for job_id in cur_job_ids
                     if job_id in prev_job_ids]

    # log duplicate ids
    logging.info(f'found {len(cur_dict.keys())} unique job ids and '
                 f'{len(duplicate_ids)} duplicates from {provider}')


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

    stopwords = {'him', ')', 'why', 'wasn', 'itself', 'they', '<', 'with',
	'nor', ':', 'mightn', 'during', "haven't", ';', 'has', 'any', "it's", 'was',
	'then', 't', "mightn't", ',', 'some', '*', 'needn', '=', 'before', 'below',
	'into', 'what', "'", 'do', 'wouldn', 'been', 'both', 'did', 'had', 'she',
	"that'll", 'doing', "didn't", '#', 'too', 'o', 'them', 'is', 'which',
	"mustn't", "she's", 'doesn', 'y', "needn't", 'who', 'm', 'will', '|',
	'himself', 'hadn', 'your', '~', 'couldn', 'can', 'most', "shan't", 'am',
	'own', 'weren', 'above', 'its', 'ourselves', 'as', 'have', '[', '?', 'out',
	"weren't", 'shouldn', 'not', 'between', "don't", 'myself', 'being', '\\',
	'only', 'herself', 'few', 'we', 'me', "hasn't", 'hers', '!', 'each',
	'over', 'having', 'this', "won't", '(', 'whom', 'haven', "should've",
	'because', 'or', 'here', "wouldn't", 'how', '"', 'our', '{', 'shan',
	"shouldn't", ']', 'through', 'yourself', 'so', '_', "you'll", 'my', 'a',
	'are', 'it', 'off', 'against', "couldn't", 'when', 'once', 'while', 'be',
	'should', 'he', 'where', 's', 'such', '^', 'ours', 'than', 'don', 'at',
	'isn', '}', 'were', 'on', "hadn't", 've', 'i', 'more', 'd', "wasn't", 'his',
	"doesn't", '.', "aren't", '+', 'up', 'now', '/', 'further', 'their', 'her',
	'after', 'in', 'all', 'by', 'very', 'ain', '%', '`', 'yourselves', 'and',
	'$', 'won', 'but', 'yours', 'if', 'to', 'same', 'hasn', 'there', 'under',
	'from', 're', 'down', 'mustn', 'themselves', '-', 'didn', 'these', 'no',
	'those', 'that', 'about', '@', "isn't", 'until', 'other', 'll', 'again',
	'an', 'you', 'ma', 'of', 'for', 'aren', "you're", 'just', 'does', 'the',
	"you've", "you'd", 'theirs', '&', '>'
    }

    '''try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')'''

    # init vectorizer
    vectorizer = TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                 analyzer='word', stop_words=stopwords)

    # init list to store duplicate ids
    duplicate_ids = {}

    if prev_dict is None:
        # get query words and ids as lists
        query_ids = [job['id'] for job in cur_dict.values()]
        query_words = [job['blurb'] for job in cur_dict.values()]

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
            if np_max(sim) >= max_similarity:
                duplicate_ids.update({query_id: cur_dict.pop(query_id)})

        # log something
        logging.info(f'found {len(cur_dict.keys())} unique listings and '
                     f'{len(duplicate_ids.keys())} duplicates '
                     f'via TFIDF cosine similarity')

    # returns a dictionary of duplicates
    return duplicate_ids
