#!python
"""main script, scrapes data off several listings, pickles it,
and applies search filters"""
import sys

from typing import Union

from .config.parser import parse_config, ConfigError
from .config.validate import validate_config

from .jobfunnel import JobFunnel
from .indeed import Indeed
from .monster import Monster
from .glassdoor_base import GlassDoorBase
from .glassdoor_dynamic import GlassDoorDynamic
from .glassdoor_static import GlassDoorStatic

PROVIDERS = {
    'indeed': Indeed,
    'monster': Monster,
    'glassdoorstatic': GlassDoorStatic,
    'glassdoordynamic': GlassDoorDynamic
}


def main():
    """main function"""
    try:
        config = parse_config()
        validate_config(config)

    except ConfigError as e:
        print(e.strerror)
        sys.exit()

    # init class + logging
    jf = JobFunnel(config)
    jf.init_logging()

    # parse the master list path to update filter list
    jf.update_filterjson()

    # get jobs by either scraping jobs or loading dumped pickles
    if config['recover']:
        jf.load_pickles(config)
    elif config['no_scrape']:
        jf.load_pickle(config)
    else:
        for p in config['providers']:
            # checks to see if provider is glassdoor
            provider: Union[Monster,
                            Indeed, GlassDoorDynamic, GlassDoorStatic] = PROVIDERS[p](config)

            provider_id = provider.__class__.__name__

            try:
                provider.scrape()
                jf.scrape_data.update(provider.scrape_data)
            except Exception as e:
                jf.logger.error(
                    f'failed to scrape {provider_id}: {str(e)}')

        # dump scraped data to pickle
        jf.dump_pickle()

    # filter scraped data and dump to the masterlist file
    jf.update_masterlist()

    # done!
    jf.logger.info('done. see un-archived jobs in ' +
                   config['master_list_path'])


if __name__ == '__main__':
    main()
