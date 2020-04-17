import pytest

from collections import OrderedDict
from datetime import datetime, timedelta
from unittest.mock import patch

from jobfunnel.tools.filters import tfidf_filter, id_filter, date_filter


attr_list = [[['blurb'], 'Looking for a passionate team player that is willing to learn new technologies. Our company X is still growing at an exponential rate. In order to be a perfect fit'
              ' you must tell us your favorite movie at the interview; favorite food; and a fun fact about yourself. The ideal fit will also know Python and SDLC.'],
             [['blurb'], 'Looking for a passionate developer that is willing to learn new technologies. Our company X is still growing at an exponential rate. In order to be a perfect fit'
              ' you must tell us your favorite movie at the interview; favorite food; and your favorite programming langauge. The ideal candiadate will also know Python and SDLC.'],
             [['blurb'], 'We make the best ice cream in the world. Our company still young and growing. We have stable funding and a lot of crazy ideas to make our company grow. The ideal candidate should like ice cream.'],
             [['blurb'], 'We make the best ice cream in the world. Our company still young and growing. We have stable funding and a lot of crazy ideas to make our company grow. The ideal candidate should love ice cream and all things ice cream.'],
             ]


def test_date_filter(per_id_job_listings):
    new_job_listings = per_id_job_listings([attr_list[0], attr_list[1]])
    # assign two different dates to the job_postings
    job_date = datetime.now() - timedelta(days=10)
    new_job_listings['0']['date'] = job_date.strftime('%Y-%m-%d')
    job_date = datetime.now() - timedelta(days=3)
    new_job_listings['1']['date'] = job_date.strftime('%Y-%m-%d')
    date_filter(new_job_listings, 5)
    # assert that that jobs older than 5 days have been removed
    assert list(new_job_listings) == ['1']


def test_id_filter(per_id_job_listings):
    new_job_listings = per_id_job_listings([attr_list[0], attr_list[2]])
    # generate job listings with the same ids as new_job_listings
    previous_job_listings = per_id_job_listings([attr_list[1], attr_list[3]])
    id_filter(new_job_listings, previous_job_listings,
              new_job_listings['0']['provider'])
    # assert that the new job listings have been removed since they already exist
    assert len(new_job_listings) == 0
    # assert that the correct job ids are in the new filtered new_job_listings
    assert list(previous_job_listings) == ['0', '1']


def test_tfidf_filter_no_previous_scrape(per_id_job_listings):
    new_job_listings = per_id_job_listings(attr_list[0:4])
    tfidf_filter(new_job_listings)
    # assert that the correct job ids are in the new filtered new_job_listings
    assert list(new_job_listings) == ['1', '3']


def test_tfidf_filter_with_previous_scrape(per_id_job_listings):
    new_job_listings = per_id_job_listings([attr_list[0], attr_list[2]])
    # generate job listings with different job ids than new_job_listings
    previous_job_listings = per_id_job_listings(
        [attr_list[1], attr_list[3]], first_job_id=2)
    tfidf_filter(new_job_listings, previous_job_listings)
    # assert that the new job listings have been removed since they already exist
    assert len(new_job_listings) == 0
    # assert that the correct job ids are in the new filtered new_job_listings
    assert list(previous_job_listings) == ['2', '3']
