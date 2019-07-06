## Paul McInnis 2018
## writes pickles to master list path and applies search filters

import pickle
import json
import logging
import os
import sys
import csv
from datetime import date
from typing import Dict
from .tools.filters import tfidf_filter

# setting job status to these words removes them from masterlist + adds to blacklist
REMOVE_STATUSES = ['archive', 'archived', 'remove', 'rejected']

# csv header:
MASTERLIST_HEADER = ['status', 'title', 'company', 'location', 'date', 'blurb',
                     'link', 'id']

class JobFunnel(object):
    """class that writes pickles to master list path and applies search filters"""

    def __init__(self, args):
        # paths
        self.master_list_path = args['master_list_path']
        self.filterlist_path = args['filter_list_path']
        self.blacklist = args['black_list']
        self.logfile = args['log_path']
        self.loglevel = args['log_level']
        self.pickles_dir = args['data_path']

        # other inits
        self.filterlist = None
        self.similar_results = args['similar']
        self.bs4_parser = 'lxml'
        self.scrape_data = {}

        # date string for pickle files
        self.date_string = date.today().strftime("%Y-%m-%d")

        # search term configuration data
        self.search_terms = args['search_terms']

        # create data dir
        if not os.path.exists(args['data_path']): os.makedirs(args['data_path'])

    def init_logging(self):
        # initialise logging to file
        self.logger = logging.getLogger()
        self.logger.setLevel(self.loglevel)
        logging.basicConfig(filename=self.logfile, level=self.loglevel)
        logging.getLogger().addHandler(logging.StreamHandler())
        self.logger.info('jobfunnel initialized at {}'.format(self.date_string))

    def scrape(self):
        """ to be implemented by child classes"""
        raise NotImplementedError()

    def load_pickle(self):
        # try to load today's pickle from set var first:
        pickle_filepath = os.path.join(args['data_path'], 'scraped',
            'jobs_{0}.pkl'.format(self.date_string))
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

    def remove_jobs_in_filterlist(self, data: Dict[str, dict]):
        ## load the filter-list if it exists, apply it to remove scraped jobs
        if data == {}:
            raise ValueError("no scraped job data to filter")

        if os.path.isfile(self.filterlist_path):
            self.filterlist = json.load(open(self.filterlist_path, 'r'))
            n_filtered = 0
            for jobid in self.filterlist:
                if jobid in data:
                    data.pop(jobid)
                    n_filtered += 1
            logging.info(f'removed {n_filtered} jobs present in filter-list'
                         ' from master-list')
        else:
            self.logger.warning(
                f'no jobs filtered, missing {self.filterlist_path}')

    def remove_blacklisted_companies(self, data: Dict[str, dict]):
        ## remove blacklisted companies from the scraped data
        # @TODO allow people to add companies to this via 'blacklist' status
        blacklist_ids = []
        for job_id, job_data in data.items():
            if job_data['company'] in self.blacklist:
                blacklist_ids.append(job_id)
        logging.info(
            f'removed {len(blacklist_ids)} jobs in black-list from master-list')
        for job_id in blacklist_ids:
            data.pop(job_id)

    def update_filterjson(self):
        ## parse master .csv file into an update for the filter-list .json file
        if os.path.isfile(self.master_list_path):
            # load existing filtered jobs, if any
            if os.path.isfile(self.filterlist_path):
                filtered_jobs = json.load(open(self.filterlist_path,'r'))
            else:
                filtered_jobs = {}

            # add jobs from csv that need to be filtered away, if any
            for job in self.read_csv(self.master_list_path, key_by_id=False):
                if job['status'] in REMOVE_STATUSES:
                    if job['id'] not in filtered_jobs:
                        logging.info('added {} to {}'.format(
                            job['id'], self.filterlist_path))
                    filtered_jobs[job['id']] = job

            # write out the complete list with any additions from the masterlist
            with open(self.filterlist_path, 'w', encoding='utf8') as outfile:
                outfile.write(
                    json.dumps(
                        filtered_jobs,
                        indent=4,
                        sort_keys=True,
                        separators=(',', ': '),
                        ensure_ascii=False))

            # update class attribute
            self.filterlist = filtered_jobs
        else:
            logging.warning("no master-list, filter-list was not updated")

    def update_masterlist(self):
        ## use the scraped job listings to update the master spreadsheet
        if self.scrape_data == {}:
            raise ValueError("No scraped jobs, cannot update masterlist")

        # filter out scraped jobs we have rejected, archived or blacklisted
        self.remove_jobs_in_filterlist(self.scrape_data)
        self.remove_blacklisted_companies(self.scrape_data)

        # load and update existing masterlist
        try:
            # open master list if it exists & init updated master-list
            masterlist = self.read_csv(self.master_list_path)

            # update masterlist to remove filtered/blacklisted jobs
            self.remove_jobs_in_filterlist(masterlist)
            self.remove_blacklisted_companies(masterlist)

            # update masterslist to contain only new (unqiue) listings
            tfidf_filter(self.scrape_data, masterlist)
            masterlist.update(self.scrape_data)

            # save
            self.write_csv(data=masterlist, path=self.master_list_path)

        except FileNotFoundError:
            # dump the results into the data folder as the master-list
            self.write_csv(data=self.scrape_data, path=self.master_list_path)
            logging.info(
                f'no masterlist detected, added {len(self.scrape_data.keys())}'
                f' jobs to {self.master_list_path}')
