## Paul McInnis 2018
## writes pickles to masterlist_path and applies search filters

import pickle
import json
import logging
import os
import sys
import csv
from datetime import date

# csv header:
MASTERLIST_HEADER = ['status', 'title', 'company', 'location', 'date', 'blurb', 'link', 'id']

class JobPy(object):
    """class that writes pickles to masterlist_path and applys search filters"""

    def __init__(self, args):
        # paths
        self.masterlist_path = args['MASTERLIST_PATH']
        self.filterlist_path = args['FILTERLIST_PATH']
        self.blacklist_path = args['BLACKLIST_PATH']
        self.logfile = args['LOG_PATH']
        self.loglevel = args['LOG_LEVEL']
        self.pickles_dir = args['DATA_PATH']

        # other inits
        self.filterlist = None
        self.similar_results = args['SIMILAR']
        self.bs4_parser = args['BS4_PARSER']
        self.scrape_data = {}

        # date string for pickle files
        self.date_string = date.today().strftime("%Y-%m-%d")

        # search term configuration data
        self.search_terms = json.load(open(args['SEARCHTERMS_PATH'], 'rb'))

        # set the search keywords if provided one
        if args['KEYWORDS']:
            self.search_terms['keywords'] = args['KEYWORDS']

        # create dirs
        if not os.path.exists('data'): os.makedirs('data')
        if not os.path.exists(args['DATA_PATH']): os.makedirs(args['DATA_PATH'])

        # handle Python 2 & 3 Unicode formatting
        try:
            self.encoding = unicode
        except NameError: # @TODO use sys.version_info instead
            self.encoding = str

    def init_logging(self):
        # initialise logging to file
        self.logger = logging.getLogger()
        self.logger.setLevel(self.loglevel)
        logging.basicConfig(filename=self.logfile, level=self.loglevel)
        logging.getLogger().addHandler(logging.StreamHandler())
        self.logger.info('jobpy initialized at {0}'.format(self.date_string))

    def scrape(self):
        """ to be implemented by child classes"""
        raise NotImplementedError()

    def load_pickle(self):
        # try to load today's pickle from set var first:
        pickle_filepath = os.path.join(
            'data', 'scraped', 'jobs_{0}.pkl'.format(self.date_string))
        try:
            self.scrape_data = pickle.load(open(pickle_filepath, 'rb'))
        except FileNotFoundError as e:
            logging.error('{} not found! Have you scraped any jobs '
                          'today?'.format(pickle_filepath))
            raise e

    def dump_pickle(self):
        """ dump a pickle of the daily scrape dict"""
        pickle_name = 'jobs_{0}.pkl'.format(self.date_string)
        pickle.dump(self.scrape_data,
                    open(os.path.join(self.pickles_dir, pickle_name), 'wb'))

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
        with open(path, 'w', encoding='utf8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(data[row])

    def filter_jobs(self):
        ## load the filter-list if it exists, apply it to remove scraped jobs
        if self.scrape_data == {}:
            raise ValueError("no scraped job data to filter")

        if not self.filterlist:
            if os.path.isfile(self.filterlist_path):
                self.filterlist = json.load(open(self.filterlist_path, 'r'))
            else:
                self.logger.warning("no jobs filtered, missing {}".format(
                    self.filterlist_path))
        # pop filtered
        n_filtered = 0
        for jobid in self.filterlist:
            if jobid in self.scrape_data:
                self.scrape_data.pop(jobid)
                n_filtered += 1

        logging.info('removed {0} jobs present in filter-list '
                     'from masterlist_path'.format(n_filtered))

    def filter_companies(self):
        ## remove blacklisted companies from the scraped data
        # @TODO allow people to add companies to this via 'blacklist' status
        try:
            self.blacklist = json.load(open(self.blacklist_path, 'r'))
            blacklist_ids = []
            for jobid in self.scrape_data:
                if self.scrape_data[jobid]['company'] in self.blacklist:
                    blacklist_ids.append(jobid)
            logging.info ('removed {0} jobs in black-list from '
                          'master-list'.format(len(blacklist_ids)))
            for jobid in blacklist_ids:
                self.scrape_data.pop(jobid)
        except FileNotFoundError:
            logging.warning('no company blacklist loaded, missing {}'.format(
                self.blacklist_path))
            self.blacklist = []

    def masterlist_to_filterjson(self):
        ## parse master .csv file into an update for the filter-list .json file
        if os.path.isfile(self.masterlist_path):
            # load existing filtered jobs, if any
            if os.path.isfile(self.filterlist_path):
                filtered_jobs = json.load(open(self.filterlist_path,'r'))
            else:
                filtered_jobs = {}

            # add jobs from csv that need to be filtered away, if any
            for job in self.read_csv(self.masterlist_path, key_by_id=False):
                if job['status'] in ['archive', 'rejected']:
                    if job['id'] not in filtered_jobs:
                        logging.info('appended {} to {}'.format(
                            job['id'], self.filterlist_path))
                    filtered_jobs[job['id']] = job

            # write out the complete list with any additions from the masterlist_path
            with open(self.filterlist_path, 'w', encoding='utf8') as outfile:
                str_ = json.dumps(filtered_jobs,
                                  indent=4,
                                  sort_keys=True,
                                  separators=(',', ': '),
                                  ensure_ascii=False)
                outfile.write(self.encoding(str_))

            # update class attribute
            self.filterlist = filtered_jobs
        else:
            logging.warning("no master-list, cannot update filter-list")

    def filter_and_update_masterlist(self):
        ## use the scraped job listings to update the master spreadsheet
        if self.scrape_data == {}:
            raise ValueError("No scraped jobs, cannot update masterlist")

        # filter out jobs we rejected / archived
        self.filter_jobs()

        # filter out jobs which are posted by black-listed companies
        self.filter_companies()

        try:
            # open master list if it exists & init updated master-list
            masterlist_path = self.read_csv(self.masterlist_path)
            # identify the new job id's not in master list or in filter-list
            for jobid in self.scrape_data:
                # preserve custom states
                if jobid in masterlist_path:
                    if self.scrape_data[jobid]['status'] != 'archive':
                        self.scrape_data[jobid]['status'] = \
                            masterlist_path[jobid]['status']
                else:
                    logging.info ('job {0} missing from search results'.format(
                        jobid))
            # save
            self.write_csv(data=self.scrape_data, path=self.masterlist_path)

        except FileNotFoundError:
            # dump the results into the data folder as the master-list
            logging.info(
                'no masterlist detected, adding {} found jobs to {}'.format(
                    len(self.scrape_data.keys()), self.masterlist_path))

            self.write_csv(data=self.scrape_data, path=self.masterlist_path)
