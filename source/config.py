## definitions go here
import logging, os

default_args = {
    # paths:
    'MASTERLIST_PATH' : os.path.join('data', 'jobs_masterlist.xlsx'),
    'FILTERLIST_PATH' : os.path.join('data', 'filterlist.json'),
    "SEARCHTERMS_PATH"  : 'search_terms.json',
    # logging config:
    'LOG_PATH'  : 'jobpy.log',
    'LOG_LEVEL' : logging.INFO,
    # other config
    'BS4_PARSER' : 'lxml',
    'RESULTS_PER_PAGE' : 50,
}

