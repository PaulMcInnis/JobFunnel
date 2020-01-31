
#Function which receives data from the SQS Queue
import sys

from typing import Union

from jobfunnel import JobFunnel
from indeed import Indeed
from monster import Monster
from glassdoor import GlassDoor
PROVIDERS = {'indeed': Indeed, 'monster': Monster, 'glassdoor': GlassDoor}


event = {
    'city': 'Bengaluru',
    'providers': ['indeed', 'monster', 'glassdoor'],
    'keyword' : ['hackerrank'],
    'country' : 'India'
}

def lambda_handler(event):
    try:
        config =    {
                        'output_path': 'search',
                        'providers': event['providers'],
                        'search_terms': {
                                            'region': {
                                                            'city': event['city'], 
                                                            'country': event['country'],
                                                            'radius': 25
                                                      },
                                            'keywords': event['keyword']
                                        }, 
                        'black_list': ['Infox Consulting'],
                        'log_level': 20, 
                        'similar': False,
                        'no_scrape': False,
                        'recover': False,
                        'save_duplicates': False,
                        'delay_config': {
                                            'function': 'linear',
                                            'delay': 10.0,
                                            'min_delay': 1.0,
                                            'random': False,
                                            'converge': False
                                        },
                        'data_path': 'search/data',
                        'master_list_path': 'search/master_list.csv',
                        'duplicate_list_path': 'search/duplicate_list.csv',
                        'filter_list_path': 'search/data/filter_list.json',
                        'log_path': 'search/data/jobfunnel.log', 'proxy': None
                    }
       # validate_config(config)
    except Exception as e:
        print(e)
        #print(e.strerror)
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
            provider: Union[GlassDoor, Monster, Indeed] = PROVIDERS[p](config)
            provider_id = provider.__class__.__name__
            try:
                provider.scrape()
                jf.scrape_data.update(provider.scrape_data)
            except Exception as e:
                jf.logger.error(f'failed to scrape {provider_id}: {str(e)}')

        # dump scraped data to pickle
        jf.dump_pickle()

    # filter scraped data and dump to the masterlist file
    jf.update_masterlist()

    # done!
    jf.logger.info(
        "done. see un-archived jobs in " + config['master_list_path'])


lambda_handler(event)
    






    