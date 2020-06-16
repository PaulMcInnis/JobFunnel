CONFIG_TYPES = {
    'output_path': [str],
    'providers': [list],
    'search_terms': {
        'region': {
            'province': [str],
            'state': [str],
            'city': [str],
            'domain': [str],
            'radius': [int]
        },
        'keywords': [list]
    },
    'black_list': [list],
    'log_level': [str],
    'similar': [bool],
    'no_scrape': [bool],
    'recover': [bool],
    'save_duplicates': [bool],
    'delay_config': {
        'function': [str],
        'delay': [float, int],
        'min_delay': [float, int],
        'random': [bool],
        'converge': [bool]
    },
    'proxy': {
        'protocol': [str],
        'ip_address': [str],
        'port': [str]
    },
    'max_listing_days': [int],

}

PROVIDERS = ['glassdoordynamic', 'glassdoorstatic', 'indeed', 'monster']
DOMAINS = ['com', 'ca']
DELAY_FUN = ['constant', 'linear', 'sigmoid']
