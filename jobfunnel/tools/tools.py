## tools for job scraping

import logging
import re
import string
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def filter_non_printables(job):
    """function that filters trailing characters in scraped strings"""
    if not job['blurb']:
        return job['blurb']

    # filter all of the weird characters some job postings have...
    printable = set(string.printable)
    job['blurb'] = ''.join(filter(lambda x: x in printable, job['blurb']))
    return job['blurb']


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
