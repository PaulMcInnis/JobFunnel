CONFIG_TYPES = {
    'output_path': str,
    'providers': list,
    'search_terms': {
        'region': {
            'province': str,
            'city': str,
            'domain': str,
            'radius': int
        },
        'keywords': list
    },
    'black_list': list,
    'log_level': str,
    'similar': bool,
    'no_scrape': bool,
    'recover': bool,
    'save_duplicates': bool,
    'set_delay': bool,
    'delay_config': {
        'function': str,
        'delay': float,
        'min_delay': float,
        'random': bool,
        'converge': bool
    }
}

PROVIDERS = ['glassdoor', 'indeed', 'monster']
DOMAINS = ['com', 'ca']
DELAY_FUN = ['constant', 'linear', 'sigmoid']