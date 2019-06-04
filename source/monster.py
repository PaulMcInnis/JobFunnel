## scrapes data off monster.ca and pickles it

import pickle
import logging
import requests
import bs4
import lxml
import re
import os
import string
from math import ceil
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from config.settings import MASTERLIST_HEADER

# the maximum monster search results per page
monster_max_results_per_page = 25


def scrape_monster_to_pickle(jobpy_obj):
    try:
        ## scrape a page of monster results to a pickle
        logging.info(
            'jobpy monster to pickle running @ : ' + jobpy_obj.date_string)

        # form the query string
        for i, s in enumerate(jobpy_obj.search_terms['keywords']):
            if i == 0:
                query = s
            else:
                query += '-' + s

        # build the job search URL
        search = 'https://www.monster.{0}/jobs/search/?q={1}&where={2}__2C-{3}' \
                 '&intcid=skr_navigation_nhpso_searchMain&rad={4}&where={2}__2c-{3}'.format(
            jobpy_obj.search_terms['region']['domain'],
            query,
            jobpy_obj.search_terms['region']['city'],
            jobpy_obj.search_terms['region']['province'],
            jobpy_obj.search_terms['region']['radius'])

        # get the HTML data, initialize bs4 with lxml
        request_HTML = requests.get(search)
        soup_base = bs4.BeautifulSoup(request_HTML.text, jobpy_obj.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find('h2', 'figure').text.strip()
        num_results = re.sub('\(', '', num_results)
        num_results = re.sub('[a-zA-Z ]*\)', '', num_results)
        num_results = int(num_results)
        logging.info(
            'Found {0} monster results for query={1}'.format(num_results,
                                                             query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / monster_max_results_per_page))
        page_url = '{0}&start={1}'.format(search, pages)
        logging.info(
            'getting monster pages 1 to {0} : {1}'.format(pages, page_url))
        jobs = bs4.BeautifulSoup(requests.get(page_url).text,
                                 jobpy_obj.bs4_parser).find_all('div',
                                                                attrs={
                                                                    'class': 'flex-row'})
        list_of_job_soups.extend(jobs)

        # make a dict of job postings from the listing briefs
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('h2', attrs={
                    'class': 'title'}).text.strip()
                job['company'] = s.find('div',
                                        attrs={'class': 'company'}).text.strip()
                job['location'] = s.find('div', attrs={
                    'class': 'location'}).text.strip()
            except AttributeError:
                continue

            # no blurb is available in monster job soups
            job['blurb'] = ''

            try:
                job['date'] = s.find('time').text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                job['id'] = str(
                    s.find('a', attrs={'data-bypass': 'true'}).get(
                        'data-m_impr_j_jobid'))
                job['link'] = str(
                    s.find('a', attrs={'data-bypass': 'true'}).get(
                        'href'))
            except (AttributeError):
                job['id'] = ''
                job['link'] = ''

            # calculate the date from relative post age
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
                            # must be from the 1970's
                            post_date = datetime(1970, 1, 1)
                            logging.error(
                                'unknown date for job {0}'.format(job['id']))
            job['date'] = post_date.strftime('%d, %b %Y')

            # key by id
            jobpy_obj.daily_scrape_dict[str(job['id'])] = job

        # save the resulting jobs dict as a pickle file
        pickle_name = 'jobs_{0}.pkl'.format(jobpy_obj.date_string)
        pickle.dump(jobpy_obj.daily_scrape_dict,
                    open(os.path.join(jobpy_obj.pickles_dir, pickle_name),
                         'wb'))
        logging.info(
            'monster pickle file successfully dumped to ' + pickle_name)
    except error as e:
        logging.info('scrape monster to pickle failed @ : ' + str(e))
        pass
