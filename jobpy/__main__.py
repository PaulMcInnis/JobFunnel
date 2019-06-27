#!python
"""Main script.

Scrapes data off several listings, pickles it, and applies search filters.
"""
import argparse

from .config.settings import default_args
from .jobpy import JobPy

# TODO: should indeed, monster, and glassdoor be subclasses of some basic class?
from .indeed import Indeed
from .monster import Monster
from .glassdoor import GlassDoor

def parse_args():
    """Parse the command line arguments.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-o',
        dest='MASTERLIST_PATH',
        action='store',
        required=False,
        default=default_args['MASTERLIST_PATH'],
        help='path to a .csv spreadsheet file used to view and filter jobs'
             ' one will be created if one does not exist at location specified'
             ' default location is ' + default_args['MASTERLIST_PATH'])

    parser.add_argument('-kw',
        dest='KEYWORDS',
        nargs='*',
        required=False,
        help='list of keywords to use in the job search. ex: Engineer, AI'
             '. Warning! all search results will be saved into .csv! '
             'Default is loaded from ' + default_args['SEARCHTERMS_PATH'])

    parser.add_argument('--similar',
        dest='SIMILAR',
        action='store_true',
        help='pass to get \'similar\'job listings to search on indeed')

    parser.add_argument('--no_scrape',
        dest='NO_SCRAPE',
        action='store_true',
        help='skip web-scraping and load pickle @ ' + default_args['DATA_PATH'])

    return parser.parse_args()

def main():
    """Main function.

    """
    args = vars(parse_args())

    # some more defaults not set by argparse rn:
    args.update({'FILTERLIST_PATH'  : default_args['FILTERLIST_PATH'],
                 'BLACKLIST_PATH'   : default_args['BLACKLIST_PATH'],
                 'LOG_PATH'         : default_args['LOG_PATH'],
                 'BS4_PARSER'       : default_args['BS4_PARSER'],
                 'LOG_LEVEL'        : default_args['LOG_LEVEL'],
                 'DATA_PATH'        : default_args['DATA_PATH'],
                 'SEARCHTERMS_PATH' : default_args['SEARCHTERMS_PATH'],
                 })

    # init class + logging
    jp = JobPy(args)
    jp.init_logging()

    # parse the masterlist_path to update filter list
    jp.masterlist_to_filterjson()

    # get jobs by either scraping jobs or loading today's dumped pickle
    if args['NO_SCRAPE']:
        jp.load_pickle()
    else:
        # @TODO pass more data via JobPy init args
        for provider in (Indeed(args), Monster(args), GlassDoor(args)):
            try:
                provider.scrape()
                jp.scrape_data.update(provider.scrape_data)
            except Exception as e:
                jp.logger.error('failed to scrape {}: {}'.format(
                    provider.__class__.__name__, str(e)))

        # dump scraped data to pickle
        jp.dump_pickle()

    # filter scraped data and dump to the masterlist file
    jp.filter_and_update_masterlist()

    # done!
    jp.logger.info("done. see un-archived jobs in " + args['MASTERLIST_PATH'])

if __name__ == '__main__':
    main()
