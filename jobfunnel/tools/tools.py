## tools for job scraping

import logging
import re
import string
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


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

    # Supports almost all formats like 7 hours|days and 7 hr|d|+d
    try:
        # hours old
        hours_ago = re.findall(r'(\d+)(?:[ +]{1,3})?(?:hour|hr)', job['date'])[
            0]
        post_date = datetime.now() - timedelta(hours=int(hours_ago))
    except IndexError:
        # days old
        try:
            days_ago = \
                re.findall(r'(\d+)(?:[ +]{1,3})?(?:day|d)', job['date'])[0]
            post_date = datetime.now() - timedelta(days=int(days_ago))
        except IndexError:
            # months old
            try:
                months_ago = \
                    re.findall(r'(\d+)(?:[ +]{1,3})?month', job['date'])[
                        0]
                post_date = datetime.now() - relativedelta(
                    months=int(months_ago))
            except IndexError:
                # years old
                try:
                    years_ago = \
                        re.findall(r'(\d+)(?:[ +]{1,3})?year',
                                   job['date'])[
                            0]
                    post_date = datetime.now() - relativedelta(
                        years=int(years_ago))
                except:
                    pass

    # try phrases like today, just posted, or yesterday
    if re.findall(r'[tT]oday|[jJ]ust [pP]osted', job['date']) and not post_date:
        # today
        post_date = datetime.now()
    elif re.findall(r'[yY]esterday', job['date']):
        # yesterday
        post_date = datetime.now() - timedelta(days=int(1))
    elif not post_date:
        # must be from the 1970's
        post_date = datetime(1970, 1, 1)
        logging.error(
            'unknown date for job {}'.format(job['id']))

    job['date'] = post_date.strftime('%Y-%m-%d')
    return job['date']
