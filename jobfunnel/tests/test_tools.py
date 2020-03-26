import pytest
from datetime import datetime, timedelta

from ..tools.tools import split_url, proxy_dict_to_url, config_factory, post_date_from_relative_post_age, filter_non_printables

from dateutil.relativedelta import relativedelta

URLS = [
    {
        'url': 'https://192.168.178.20:812',
        'splits': {
            'protocol': 'https',
            'ip_address': '192.168.178.20',
            'port': '812'
        },
        'complete': True
    },
    {
        'url': '1.168.178.20:812',
        'splits': {
            'protocol': '',
            'ip_address': '1.168.178.20',
            'port': '812'
        },
        'complete': False
    },
    {
        'url': 'https://192.168.178.20',
        'splits': {
            'protocol': 'https',
            'ip_address': '192.168.178.20',
            'port': ''
        },
        'complete': False
    },
    {
        'url': '192.168.178.20',
        'splits': {
            'protocol': '',
            'ip_address': '192.168.178.20',
            'port': ''
        },
        'complete': False
    }
]

# Define a attribute list for all tests to use in this module

attr_list = [
    [['title'], 'Test Engineer'],
    [['title'], 'Software Engineer–'],
    [['blurb'], 'Test and develop'],
    [['blurb'], 'Develop and design software–'],
    [['date'], 'Just posted'],
    [['date'], 'today'],
    [['date'], '1 hour ago'],
    [['date'], '2 hours ago'],
    [['date'], 'yesterday'],
    [['date'], '1 day ago'],
    [['date'], '2 days ago'],
    [['date'], '1 month'],
    [['date'], '2 months'],
    [['date'], '1 year ago'],
    [['date'], '2 years ago'],
    [['date'], '1 epoch ago'],
    [['date'], 'junk'],
    [['some_option'], 'option_value']
]

# Test clean/dirty characters that may be on title and blurb fields


def test_filter_non_printables_clean_title(job_listings):
    job_list = job_listings(attr_list[0:1])
    filter_non_printables(job_list[0])
    assert job_list[0]['title'] == 'Test Engineer'


def test_filter_non_printables_dirty_title(job_listings):
    job_list = job_listings(attr_list[1:2])
    filter_non_printables(job_list[0])
    assert job_list[0]['title'] == 'Software Engineer'


def test_filter_non_printables_clean_blurb(job_listings):
    job_list = job_listings(attr_list[2:3])
    filter_non_printables(job_list[0])
    assert job_list[0]['blurb'] == 'Test and develop'


def test_filter_non_printables_diryt_blurb(job_listings):
    job_list = job_listings(attr_list[3:4])
    filter_non_printables(job_list[0])
    assert job_list[0]['blurb'] == 'Develop and design software'

# Test job_listing dates with all possible formats


def test_post_date_from_relative_post_age_just_posted_pass(job_listings):
    job_list = job_listings(attr_list[4:5])
    post_date_from_relative_post_age(job_list)
    assert datetime.now().strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_post_age_today_pass(job_listings):
    job_list = job_listings(attr_list[5:6])
    post_date_from_relative_post_age(job_list)
    assert datetime.now().strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_post_age_1_hour_ago_pass(job_listings):
    job_list = job_listings(attr_list[6:7])
    post_date_from_relative_post_age(job_list)
    assert datetime.now().strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_post_age_2_hours_ago_pass(job_listings):
    job_list = job_listings(attr_list[7:8])
    post_date_from_relative_post_age(job_list)
    assert datetime.now().strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_yesterday_ago_pass(job_listings):
    job_list = job_listings(attr_list[8:9])
    post_date_from_relative_post_age(job_list)
    yesterday = datetime.now() - timedelta(days=int(1))
    assert yesterday.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_1_day_ago_pass(job_listings):
    job_list = job_listings(attr_list[9:10])
    post_date_from_relative_post_age(job_list)
    one_day_ago = datetime.now() - timedelta(days=int(1))
    assert one_day_ago.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_2_days_ago_pass(job_listings):
    job_list = job_listings(attr_list[10:11])
    post_date_from_relative_post_age(job_list)
    two_days_ago = datetime.now() - timedelta(days=int(2))
    assert two_days_ago.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_1_month_ago_pass(job_listings):
    job_list = job_listings(attr_list[11:12])
    post_date_from_relative_post_age(job_list)
    one_month_ago = datetime.now() - relativedelta(months=int(1))
    assert one_month_ago.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_2_months_ago_pass(job_listings):
    job_list = job_listings(attr_list[12:13])
    post_date_from_relative_post_age(job_list)
    two_months_ago = datetime.now() - relativedelta(months=int(2))
    assert two_months_ago.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_1_year_ago_pass(job_listings):
    job_list = job_listings(attr_list[13:14])
    post_date_from_relative_post_age(job_list)
    one_year_ago = datetime.now() - relativedelta(years=int(1))
    assert one_year_ago.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_2_years_ago_pass(job_listings):
    job_list = job_listings(attr_list[14:15])
    post_date_from_relative_post_age(job_list)
    two_years_ago = datetime.now() - relativedelta(years=int(2))
    assert two_years_ago.strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_1_epoch_ago_pass(job_listings):
    job_list = job_listings(attr_list[15:16])
    post_date_from_relative_post_age(job_list)
    assert datetime(1970, 1, 1).strftime('%Y-%m-%d') == job_list[0]['date']


def test_post_date_from_relative_ago_post_age_junk(job_listings):
    job_list = job_listings(attr_list[16:17])
    post_date_from_relative_post_age(job_list)
    assert datetime(1970, 1, 1).strftime('%Y-%m-%d') == job_list[0]['date']


def test_config_factory(configure_options):
    config = config_factory(configure_options(
        ['']), attr_list[17:18])[0]
    assert config['some_option'] == 'option_value'


@pytest.mark.parametrize('url', URLS)
def test_split_url(url):
    # gives dictionary with protocol, ip and port
    url_dic = split_url(url['url'])

    # check if all elements match with provided output
    if url['complete']:
        assert url_dic == url['splits']
    else:
        assert url_dic is None


@pytest.mark.parametrize('url', URLS)
def test_proxy_dict_to_url(url):
    # gives dictionary with protocol, ip and port
    url_str = proxy_dict_to_url(url['splits'])

    # check if all elements match with provided output
    assert url_str == url['url']
