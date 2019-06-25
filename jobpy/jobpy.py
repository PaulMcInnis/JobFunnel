## Paul McInnis 2018
## writes pickles to masterlist and applies search filters

import pickle
import json
import logging
import os
import csv
from datetime import date

from .config.settings import MASTERLIST_HEADER

class jobpy(object):
    """class that writes pickles to masterlist and applys search filters"""
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
        with open(path, 'w', encoding='utf8') as csvfile:
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
