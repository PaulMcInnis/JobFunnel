import logging
import re
import string

from copy import deepcopy
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


def filter_non_printables(job):
    """function that filters trailing characters in scraped strings"""
    # filter all of the weird characters some job postings have...
    printable = set(string.printable)
    job['title'] = ''.join(filter(lambda x: x in printable, job['title']))
    job['description'] = ''.join(filter(lambda x: x in printable, job['description']))


def post_date_from_relative_post_age(job_list):
    """function that returns the post date from the relative post age"""
    # initialize list and store regex objects of date quantifiers
    date_regex = [re.compile(r'(\d+)(?:[ +]{1,3})?(?:hour|hr)'),
                  re.compile(r'(\d+)(?:[ +]{1,3})?(?:day|d)'),
                  re.compile(r'(\d+)(?:[ +]{1,3})?month'),
                  re.compile(r'(\d+)(?:[ +]{1,3})?year'),
                  re.compile(r'[tT]oday|[jJ]ust [pP]osted'),
                  re.compile(r'[yY]esterday')]

    for job in job_list:
        if not job['date']:
            return job['date']

        post_date = None

        # supports almost all formats like 7 hours|days and 7 hr|d|+d
        try:
            # hours old
            hours_ago = date_regex[0].findall(job['date'])[0]
            post_date = datetime.now() - timedelta(hours=int(hours_ago))
        except IndexError:
            # days old
            try:
                days_ago = \
                    date_regex[1].findall(job['date'])[0]
                post_date = datetime.now() - timedelta(days=int(days_ago))
            except IndexError:
                # months old
                try:
                    months_ago = \
                        date_regex[2].findall(job['date'])[0]
                    post_date = datetime.now() - relativedelta(
                        months=int(months_ago))
                except IndexError:
                    # years old
                    try:
                        years_ago = \
                            date_regex[3].findall(job['date'])[0]
                        post_date = datetime.now() - relativedelta(
                            years=int(years_ago))
                    except IndexError:
                        # try phrases like today, just posted, or yesterday
                        if date_regex[4].findall(
                                job['date']) and not post_date:
                            # today
                            post_date = datetime.now()
                        elif date_regex[5].findall(job['date']):
                            # yesterday
                            post_date = datetime.now() - timedelta(days=int(1))
                        elif not post_date:
                            # must be from the 1970's
                            post_date = datetime(1970, 1, 1)
                            logging.error(f"unknown date for job {job['id']}")
        # format date in standard format e.g. 2020-01-01
        job['date'] = post_date.strftime('%Y-%m-%d')
   

def split_url(url):
    # capture protocol, ip address and port from given url
    match = re.match(r'^(http[s]?):\/\/([A-Za-z0-9.]+):([0-9]+)?(.*)$', url)

    # if not all groups have a match, match will be None
    if match is not None:
        return {
            'protocol': match.group(1),
            'ip_address': match.group(2),
            'port': match.group(3),
        }
    else:
        return None


def proxy_dict_to_url(proxy_dict):
    protocol = proxy_dict['protocol']
    ip = proxy_dict['ip_address']
    port = proxy_dict['port']

    url_str = ''
    if protocol != '':
        url_str += protocol + '://'
    if ip != '':
        url_str += ip
    if port != '':
        url_str += ':' + port
      
    return url_str


def change_nested_dict(data, args, val):
    """ Access nested dictionary using multiple arguments.

    https://stackoverflow.com/questions/10399614/accessing-value-inside-nested-dictionaries
    """
    if args and data:
        element = args[0]
        if element:
            if len(args) == 1:
                data[element] = val
            else:
                change_nested_dict(data[element], args[1:], val)


def config_factory(base_config, attr_list):
    """ Create new config files from attribute dictionary.

    """
    configs = []
    for attr in attr_list:
        # create deep copy of nested dict
        config_cp = deepcopy(base_config)

        # change value and append
        change_nested_dict(config_cp, attr[0], attr[1])
        configs.append(config_cp)

    return configs
