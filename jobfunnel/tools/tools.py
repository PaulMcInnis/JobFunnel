## tools for job scraping

import logging
import re
import string
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# user agent list
# https://developers.whatismybrowser.com/useragents/explore/
user_agent_list = [
    # chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    # firefox
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
]

def filter_non_printables(job):
    """function that filters trailing characters in scraped strings"""
    # filter all of the weird characters some job postings have...
    printable = set(string.printable)
    job['title'] = ''.join(filter(lambda x: x in printable, job['title']))
    job['blurb'] = ''.join(filter(lambda x: x in printable, job['blurb']))


def post_date_from_relative_post_age(job):
    """function that returns the post date from the relative post age"""
    if not job['date']:
        return job['date']

    post_date = None

    # try known phrases like 7 hours ago or 3 days ago
    try:
        # hours old
        hours_ago = re.findall(r'(\d+)[0-9]*.*hour.*ago', job['date'])[
            0]
        post_date = datetime.now() - timedelta(hours=int(hours_ago))
    except IndexError:
        # days old
        try:
            days_ago = \
                re.findall(r'(\d+)[0-9]*.*day.*ago', job['date'])[0]
            post_date = datetime.now() - timedelta(days=int(days_ago))
        except IndexError:
            # months old
            try:
                months_ago = \
                    re.findall(r'(\d+)[0-9]*.*month.*ago', job['date'])[
                        0]
                post_date = datetime.now() - relativedelta(
                    months=int(months_ago))
            except IndexError:
                # years old
                try:
                    years_ago = \
                        re.findall(r'(\d+)[0-9]*.*year.*ago',
                                   job['date'])[
                            0]
                    post_date = datetime.now() - relativedelta(
                        years=int(years_ago))
                except:
                    pass

    # try phrases like today or yesterday
    if re.findall(r'[tT]oday', job['date']) and not post_date:
        # today
        post_date = datetime.now()
    elif re.findall(r'[yY]esterday', job['date']):
        # yesterday
        post_date = datetime.now() - timedelta(days=int(1))

    # try phrases like 1 d or 2 d or 30d+
    if re.findall(r'[0-9]* *d.*', job['date']) and not post_date:
        # some time in the past
        post_date = datetime.now() - timedelta(
            days=int(re.sub('d.*', '', job['date'])))

    # try phrases like 24 hr
    if re.findall(r'[0-9]* *hr.*', job['date']) and not post_date:
        # some time in the past
        post_date = datetime.now() - timedelta(
            hours=int(re.sub('hr.*', '', job['date'])))

    if not post_date:
        # must be from the 1970's
        post_date = datetime(1970, 1, 1)
        logging.error(
            'unknown date for job {}'.format(job['id']))

    job['date'] = post_date.strftime('%d, %b %Y')
    return job['date']
