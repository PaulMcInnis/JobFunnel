import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
from logging import info as log_info
from math import ceil
from requests import post
from time import sleep, time

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age


class GlassDoorBase(JobFunnel):
    def __init__(self, args):
        super().__init__(args)
        self.provider = 'glassdoorbase'
        self.max_results_per_page = 30
        self.delay = 0

        self.location_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
            'image/webp,*/*;q=0.01',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                self.search_terms['region']['domain']
            ),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }

    def convert_radius(self, radius):
        """function that quantizes the user input radius to a valid radius
           value: 10, 20, 30, 50, 100, and 200 kilometers"""
        if self.search_terms['region']['domain'] == 'com':
            if radius < 5:
                radius = 0
            elif 5 <= radius < 10:
                radius = 5
            elif 10 <= radius < 15:
                radius = 10
            elif 15 <= radius < 25:
                radius = 15
            elif 25 <= radius < 50:
                radius = 25
            elif 50 <= radius < 100:
                radius = 50
            elif radius >= 100:
                radius = 100
            return radius

        else:
            if radius < 10:
                radius = 0
            elif 10 <= radius < 20:
                radius = 10
            elif 20 <= radius < 30:
                radius = 20
            elif 30 <= radius < 50:
                radius = 30
            elif 50 <= radius < 100:
                radius = 50
            elif 100 <= radius < 200:
                radius = 100
            elif radius >= 200:
                radius = 200

            glassdoor_radius = {0: 0,
                                10: 6,
                                20: 12,
                                30: 19,
                                50: 31,
                                100: 62,
                                200: 124}

            return glassdoor_radius[radius]

    def parse_blurb(self, job, html):
        """parses and stores job description into dict entry"""
        job_link_soup = BeautifulSoup(html, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescriptionContainer').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)
