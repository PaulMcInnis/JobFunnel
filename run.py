## Paul McInnis 2018
## scrapes data off indeed.ca, pickles it, and applies search filters

import argparse
import sys
from config.settings import default_args
from source.jobpy import jobpy
from source.indeed import scrape_indeed_to_pickle
from source.monster import scrape_monster_to_pickle

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', dest='MASTERLIST_PATH', action='store',
        required=False, default=default_args['MASTERLIST_PATH'],
        help='path to a .csv spreadsheet file used to view and filter jobs'
             ' one will be created if one does not exist at location specified'
             ' default location is ' + default_args['MASTERLIST_PATH'])
    parser.add_argument('-kw', dest='KEYWORDS', nargs='*', required=False,
        help='list of keywords to use in the job search. ex: Engineer, AI'
             '. Warning! all search results will be saved into .csv! '
             'Default is loaded from ' + default_args['SEARCHTERMS_PATH'])
    parser.add_argument('--similar', dest='SIMILAR', action='store_true',
        help='pass to get \'similar\'job listings to search on indeed')
    parser.add_argument('--no_scrape', dest='NO_SCRAPE', action='store_true',
        help='skip web-scraping and load pickle @ ' + default_args['DATA_PATH'])

    # parse
    args = vars(parser.parse_args(sys.argv[1:]))

    # some more defaults not set by argparse rn:
    args.update({'FILTERLIST_PATH'  : default_args['FILTERLIST_PATH'],
                 'BLACKLIST_PATH'   : default_args['BLACKLIST_PATH'],
                 'LOG_PATH'         : default_args['LOG_PATH'],
                 'BS4_PARSER'       : default_args['BS4_PARSER'],
                 'LOG_LEVEL'        : default_args['LOG_LEVEL'],
                 'DATA_PATH'        : default_args['DATA_PATH'],
                 'SEARCHTERMS_PATH' : default_args['SEARCHTERMS_PATH'],
                 })

    # init class
    jobpy_obj = jobpy(args)

    # parse the xslx to filter list, scrape new listings & add to master xslx
    jobpy_obj.masterlist_to_filterjson()
    if not args['NO_SCRAPE'] :
        jobpy_obj.daily_scrape_dict = {}
        scrape_indeed_to_pickle(jobpy_obj)
        scrape_monster_to_pickle(jobpy_obj)
    jobpy_obj.pickle_to_masterlist()

    print ("done.\nsee un-archived jobs in " + args['MASTERLIST_PATH'])
