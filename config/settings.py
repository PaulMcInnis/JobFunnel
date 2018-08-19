## definitions go here
import logging, os

default_args = {
    # paths:
    'MASTERLIST_PATH' : os.path.join('data', 'jobs_masterlist.csv'),
    'FILTERLIST_PATH' : os.path.join('data', 'filterlist.json'),
    'BLACKLIST_PATH'  : os.path.join('config', 'blacklist.json'),
    "SEARCHTERMS_PATH"  : os.path.join('config','search_terms.json'),
    # logging config:
    'LOG_PATH'  : 'jobpy.log',
    'LOG_LEVEL' : logging.INFO,
    # other config
    'BS4_PARSER' : 'lxml',
    'RESULTS_PER_PAGE' : 50, # appears to be the maximum allowed by indeed.ca
    'DATA_PATH' : os.path.join('data', 'scraped')
}

# csv header:
MASTERLIST_HEADER = ['status', 'title', 'company', 'location', 'date', 'blurb', 'link', 'id']
