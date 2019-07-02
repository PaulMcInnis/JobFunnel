#!python
"""Main script.

Scrapes data off several listings, pickles it, and applies search filters.
"""
from .config.parser import parse_config

from .jobpy import JobPy
from .indeed import Indeed
from .monster import Monster
from .glassdoor import GlassDoor

def main():
    """Main function.

    """
    import pprint
    pprint.pprint(parse_config())

    return 0


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
    """

if __name__ == '__main__':
    main()
