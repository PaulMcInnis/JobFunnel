import pytest

from ..tools.tools import split_url, proxy_dict_to_url


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
