## Paul McInnis 2018
## scrapes data off indeed.ca, pickles it, and applies search filters

import pickle
import json
import logging
import requests
import bs4
import lxml
import re
import os
import csv
from math import ceil
from datetime import date, datetime, timedelta
from config.settings import MASTERLIST_HEADER


class jobpy(object):

    """class to scrape data off of indeed.ca, with csv-based I/O"""

    def __init__(self, args):
        # paths
        self.masterlist = args['MASTERLIST_PATH']
        self.filterlist = args['FILTERLIST_PATH']
        self.blacklist = args['BLACKLIST_PATH']
        self.logfile = args['LOG_PATH']
        self.pickles_dir = args['DATA_PATH']

        # other inits
        self.similar_results = args['SIMILAR']
        self.bs4_parser = args['BS4_PARSER']
        self.results_per_page = args['RESULTS_PER_PAGE']
        self.daily_scrape_dict = None

        # date string for pickle files
        self.date_string = date.today().strftime("%Y-%m-%d")

        # search term configuration data
        self.search_terms = json.load(open(args['SEARCHTERMS_PATH'], 'rb'))

        # set the search keywords if provided one
        if args['KEYWORDS']:
            self.search_terms['keywords'] = args['KEYWORDS']

        # logging
        logging.basicConfig(filename=args['LOG_PATH'], level=args['LOG_LEVEL'])
        logging.info('jobpy initialized at {0}'.format(self.date_string))

        # create dirs
        if not os.path.exists('data'): os.makedirs('data')
        if not os.path.exists(args['DATA_PATH']): os.makedirs(args['DATA_PATH'])

        # handle Python 2 & 3 Unicode formatting
        try:
            self.encoding = unicode
        except NameError: # @TODO use sys.version_info instead
            self.encoding = str

    def read_csv(self, path, key_by_id=True):
        ## reads csv passed in as path
        with open(path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            if key_by_id:
                return dict([(j['id'] , j) for j in reader])
            else:
                return [row for row in reader]

    def write_csv(self, data, path, fieldnames=MASTERLIST_HEADER):
        ## writes data [dict(),..] to a csv at path
        with open(path, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(data[row])

    def masterlist_to_filterjson(self):
        ## parse master .csv file into an update for the filter-list .json file
        if os.path.isfile(self.masterlist):
            # load existing filtered jobs, if any
            if os.path.isfile(self.filterlist):
                filtered_jobs = json.load(open(self.filterlist,'r'))
            else:
                filtered_jobs = {}

            # add jobs from csv that need to be filtered away, if any
            for job in self.read_csv(self.masterlist, key_by_id=False):
                if job['status'] in ['archive', 'rejected']:
                    if job['id'] not in filtered_jobs:
                        logging.info ('appended {0} to {1}'.format(job['id'], self.filterlist))
                    filtered_jobs[job['id']] = job

            # write out the complete list with any additions from the masterlist
            with open(self.filterlist, 'w', encoding='utf8') as outfile:
                str_ = json.dumps(filtered_jobs,
                                  indent=4,
                                  sort_keys=True,
                                  separators=(',', ': '),
                                  ensure_ascii=False)
                outfile.write(self.encoding(str_))
        else:
            logging.warning ("no master-list detected, cannot update filter-list")

    def scrape_indeed_to_pickle(self):
        ## scrape a page of indeed results to a pickle
        logging.info('jobpy indeed_topickle running @ : ' + self.date_string)

        # form the query string
        for i, s in enumerate(self.search_terms['keywords']):
            if i == 0: query = s
            else: query += '+' + s

        # build the job search URL
        search = 'http://www.indeed.{0}/jobs?q={1}&l={2}%2C+{3}&radius={4}' \
                 '&limit={5}&filter={6}'.format(
                    self.search_terms['region']['domain'],
                    query, self.search_terms['region']['city'],
                    self.search_terms['region']['province'],
                    self.search_terms['region']['radius'],
                    self.results_per_page, int(self.similar_results))

        # get the HTML data, initialize bs4 with lxml
        request_HTML = requests.get(search)
        soup_base = bs4.BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find(id = 'searchCount').contents[0].strip()
        num_results = int(re.sub(".*of[^0-9]","", num_results))
        logging.info('Found {0} results for query={1}'.format(num_results, query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        for page in range(0, int(ceil(num_results/self.results_per_page))):
            page_url = '{0}&start={1}'.format(search, int(page*self.results_per_page))
            logging.info ('getting page {0} : {1}'.format(page, page_url))
            jobs = bs4.BeautifulSoup(requests.get(page_url).text,
                            self.bs4_parser).find_all('div',
                            attrs={'data-tn-component': 'organicJob'})
            list_of_job_soups.extend(jobs)

        # make a dict of job postings from the listing briefs
        self.daily_scrape_dict =  {}
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k,'') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            job['title'] = s.find('a', attrs={'data-tn-element': "jobTitle"}).text.strip()
            job['company'] = s.find('span', attrs={"class":"company"}).text.strip()
            job['blurb'] = s.find('span',{'class': 'summary'}).text.strip()
            job['location'] = s.find('span',{'class': 'location'}).text.strip()
            s.find('span', attrs={'result-link-bar' : 'date'})
            job['id'] = re.findall(r'id=\"sj_(.*)\" onclick',
                str(s.find_all('a', { "class" : "sl resultLink save-job-link "})))[0]
            job['link'] = 'http://www.indeed.{0}/viewjob?jk={1}'.format(
                           self.search_terms['region']['domain'], job['id'])

            # calculate the date from relative post age
            link_bar_text = str(s.find("div", class_="result-link-bar"))
            try:
                days_ago = re.findall(r'(\d+).*day.*ago', link_bar_text)[0]
                post_date = datetime.now() - timedelta(days=int(days_ago))
            except IndexError:
                # it's probably not days old
                try:
                    hours_ago = re.findall(r'(\d+).*hour.*ago', link_bar_text)[0]
                    post_date = datetime.now() - timedelta(hours=int(hours_ago))
                except:
                    post_date = datetime(1970,1,1)
                    logging.error('unknown date for job {0}'.format(job['id']))
            job['date'] = post_date.strftime('%d, %b %Y')

            # key by id
            self.daily_scrape_dict[str(job['id'])] = job

        # save the resulting jobs dict as a pickle file
        pickle_name = 'jobs_{0}.pkl'.format(self.date_string)
        pickle.dump(self.daily_scrape_dict,
                    open(os.path.join(self.pickles_dir,pickle_name), 'wb'))
        logging.info('pickle file successfully dumped to ' + pickle_name)


    def pickle_to_masterlist(self):
        ## use the scraped job listings to update the master spreadsheet
        # try to load it from set var first:
        if not self.daily_scrape_dict:
            # try to open the daily pickle file --> dict if it exists
            pickle_filepath = os.path.join('data', 'scraped', 'jobs_{0}.pkl'.format(
                                           self.date_string))
            try:
                self.daily_scrape_dict = pickle.load(open(pickle_filepath, 'rb'))
            except FileNotFoundError as e:
                logging.error(pickle_filepath + ' not found!')
                raise e

        # load the filterlist if it exists, and apply it to remove any filtered jobs
        if os.path.isfile(self.filterlist):
            filter_dict = json.load(open(self.filterlist, 'r'))
            n_filtered = 0
            for jobid in filter_dict:
                if jobid in self.daily_scrape_dict:
                    self.daily_scrape_dict.pop(jobid)
                    n_filtered += 1
            logging.info('found {0} jobs present in filter-list, '\
                          'not added to master-list'.format(n_filtered))
        else:
            logging.warning('missing {0}'.format(self.filterlist))

        # apply company blacklist
        try:
            company_blacklist = json.load(open(self.blacklist, 'r'))
            blacklisted_ids = []
            for jobid in self.daily_scrape_dict:
                if self.daily_scrape_dict[jobid]['company'] in company_blacklist:
                    blacklisted_ids.append(jobid)
            logging.info ('found {0} jobs present in blacklist, not added '\
                          'to master-list'.format(len(blacklisted_ids)))
            for jobid in blacklisted_ids:
                self.daily_scrape_dict.pop(jobid)
        except FileNotFoundError:
            logging.warning('{0} not found!, no company filtration'.format(self.blacklist))
            company_blacklist = []

        try:
            # open master list if it exists & init updated master-list
            masterlist = self.read_csv(self.masterlist)
            # identify the new job id's not in master list or in filter-list
            for jobid in self.daily_scrape_dict:
                # preserve custom states
                if jobid in masterlist:
                    if self.daily_scrape_dict[jobid]['status'] != 'archive':
                        self.daily_scrape_dict[jobid]['status'] = masterlist[jobid]['status']
                else:
                    logging.info ('job {0} missing from search results'.format(jobid))
                    # assume job in the masterlist not in search results = expired
                    #self.daily_scrape_dict[jobid]['status'] = 'expired'
                    # @TODO it seems that sponsored jobs change, and this affects status
            # save
            self.write_csv(data=self.daily_scrape_dict, path=self.masterlist)

        except FileNotFoundError:
            # dump the results into the data folder as the master-list
            logging.info ('no masterlist detected, adding {0} found jobs to {1}'.format(
                len(self.daily_scrape_dict.keys()), self.masterlist))
            self.write_csv(data=self.daily_scrape_dict, path=self.masterlist)
