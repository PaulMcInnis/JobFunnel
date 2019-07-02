#!python
"""Main script.

Scrapes data off several listings, pickles it, and applies search filters.
"""
from .config.parser import parse_config

from .jobpy import JobPy
from .indeed import Indeed
from .monster import Monster
from .glassdoor import GlassDoor

providers = {'indeed': Indeed, 'monster': Monster, 'glassdoor': GlassDoor}

def main():
    """Main function.

    """
    config = parse_config()

    # init class + logging
    jp = JobPy(config)
    jp.init_logging()

    # parse the master list path to update filter list
    jp.masterlist_to_filterjson()

    # get jobs by either scraping jobs or loading today's dumped pickle
    if config['no_scrape']:
        jp.load_pickle()
    else:
        for p in config['providers']:
            provider = providers[p](config)
            provider_id = provider.__class__.__name__
            try:
                provider.scrape()
                jp.scrape_data.update(provider.scrape_data)
            except Exception as e:
                jp.logger.error(f'failed to scrape {provider_id}: {str(e)}')

        # dump scraped data to pickle
        jp.dump_pickle()

    # filter scraped data and dump to the masterlist file
    jp.filter_and_update_masterlist()

    # done!
    jp.logger.info("done. see un-archived jobs in " + config['master_list_path'])

if __name__ == '__main__':
    main()
