## Paul McInnis 2018
## scrapes data off indeed.ca, pickles it, and applies search filters

import argparse
import sys
from config.settings import default_args
from source.jobpy import jobpy

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', dest='MASTERLIST_PATH', action='store',
        required=False, default=default_args['MASTERLIST_PATH'],
        help='path to a .xlsx spreadsheet file used to view and filter jobs'
             ' one will be created if one does not exist at location specified')
    parser.add_argument('-f', dest='FILTERLIST_PATH', action='store',
        required=False, default=default_args['FILTERLIST_PATH'],
        help='path to a .json file which contains jobs rejected from the .xlsx'
             ' one will be created if one does not exist at location specified')
    parser.add_argument('-t', dest='SEARCHTERMS_PATH', action='store',
        required=False, default=default_args['SEARCHTERMS_PATH'],
        help='path to a .json file which contains the desired search config'
             ' one will be created if one does not exist at location specified')
    parser.add_argument('--similar', dest='SIMILAR', action='store_true',
        help='set to true to get \'similar\'job listings on indeed')

    args = vars(parser.parse_args(sys.argv[1:]))

    # some more defaults not set by argparse rn:
    args.update({'LOG_PATH'         : default_args['LOG_PATH'],
                 'BS4_PARSER'       : default_args['BS4_PARSER'],
                 'RESULTS_PER_PAGE' : default_args['RESULTS_PER_PAGE'],
                 'LOG_LEVEL'        : default_args['LOG_LEVEL'],
                 'DATA_PATH'        : default_args['DATA_PATH']
                 })

    # init class
    jobpy_interface = jobpy(args)

    # parse the xslx to filter list, scrape new listings & add to master xslx
    jobpy_interface.masterlist_to_filterjson()
    jobpy_interface.scrape_indeed_to_pickle()
    jobpy_interface.pickle_to_masterlist()

    print ("done")
