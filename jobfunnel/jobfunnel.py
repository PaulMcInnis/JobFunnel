# Paul McInnis 2018
# writes pickles to master list path and applies search filters

import csv
import json
import logging
import os
import pickle
import random
import re
import sys

from collections import OrderedDict
from concurrent.futures import as_completed
from datetime import date
from time import time
from typing import Dict, List
from requests import Session

from .tools.delay import delay_alg
from .tools.filters import tfidf_filter, id_filter, date_filter
from .tools.tools import proxy_dict_to_url

# setting job status to these words removes them from masterlist + adds to
# blacklist
REMOVE_STATUSES = ['archive', 'archived', 'remove', 'rejected']

# csv header
MASTERLIST_HEADER = ['status', 'title', 'company', 'location', 'date',
                     'blurb', 'tags', 'link', 'id', 'provider', 'query']

# user agent list
USER_AGENT_LIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'text/user_agent_list.txt'))


class JobFunnel(object):
    """class that writes pickles to master list path and applies search
    filters """

    def __init__(self, args):
        # The maximum number of days old a job can be
        self.max_listing_days = args['max_listing_days']
        # paths
        self.master_list_path = args['master_list_path']
        self.filterlist_path = args['filter_list_path']
        self.blacklist = args['black_list']
        self.logfile = args['log_path']
        self.loglevel = args['log_level']
        self.pickles_dir = args['data_path']
        self.duplicate_list_path = args['duplicate_list_path']

        # other inits
        self.filterlist = None
        self.similar_results = args['similar']
        self.save_dup = args['save_duplicates']
        self.bs4_parser = 'lxml'
        self.scrape_data = {}

        # user agent init
        user_agent_list = []
        with open(USER_AGENT_LIST) as file:
            for line in file:
                li = line.strip()
                if li and not li.startswith("#"):
                    user_agent_list.append(line.rstrip('\n'))
        self.user_agent = random.choice(user_agent_list)

        # date string for pickle files
        self.date_string = date.today().strftime("%Y-%m-%d")

        # search term configuration data
        self.search_terms = args['search_terms']

        # set delay settings if they exist
        self.delay_config = None
        if args['delay_config'] is not None:
            self.delay_config = args['delay_config']

        # set session with (potential proxy)
        self.s = Session()

        # set proxy if given
        if args['proxy'] is not None:
            self.s.proxies = {
                args['proxy']['protocol']: proxy_dict_to_url(args['proxy'])
            }

        # create data dir
        if not os.path.exists(args['data_path']):
            os.makedirs(args['data_path'])

    def init_logging(self):
        # initialise logging to file
        self.logger = logging.getLogger()
        self.logger.setLevel(self.loglevel)
        logging.basicConfig(filename=self.logfile, level=self.loglevel)
        if self.loglevel == 20:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        else:
            logging.getLogger().addHandler(logging.StreamHandler())

        self.logger.info(f'jobfunnel initialized at {self.date_string}')

    def get_search_url(self, method='get'):
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_title():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_company():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_location():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_tags():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_date():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_id():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_link():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def get_number_of_pages():
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def scrape(self):
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def load_pickle(self, args):
        """function to load today's daily scrape pickle"""
        # only to be used in no_scrape mode
        pickle_filepath = os.path.join(args['data_path'],
                                       f'jobs_{self.date_string}.pkl')
        try:
            self.scrape_data = pickle.load(open(pickle_filepath, 'rb'))
        except FileNotFoundError as e:
            logging.error(f'{pickle_filepath} not found! Have you scraped '
                          f'any jobs today?')
            raise e

    def load_pickles(self, args):
        """function to load all historic daily scrape pickles"""
        # only to be used in recovery mode
        pickle_found = False
        pickle_path = os.path.join(args['data_path'])
        for root, dirs, files in os.walk(pickle_path):
            for file in files:
                if re.findall(r'jobs_.*', file):
                    if not pickle_found:
                        pickle_found = True
                    pickle_file = file
                    pickle_filepath = os.path.join(pickle_path, pickle_file)
                    logging.info(f'loading pickle file: {pickle_filepath}')
                    self.scrape_data.update(
                        pickle.load(open(pickle_filepath, 'rb')))
        if not pickle_found:
            logging.error(f'no pickles found in {pickle_path}!'
                          f' Have you scraped any jobs?')
            raise Exception

    def dump_pickle(self):
        """function to dump a pickle of the daily scrape dict"""
        pickle_name = f'jobs_{self.date_string}.pkl'
        pickle.dump(self.scrape_data,
                    open(os.path.join(self.pickles_dir, pickle_name), 'wb'))

    def read_csv(self, path, key_by_id=True):
        # reads csv passed in as path
        with open(path, 'r', encoding='utf8', errors='ignore') as csvfile:
            reader = csv.DictReader(csvfile)
            if key_by_id:
                return dict([(j['id'], j) for j in reader])
            else:
                return [row for row in reader]

    def write_csv(self, data, path, fieldnames=MASTERLIST_HEADER):
        # writes data [dict(),..] to a csv at path
        with open(path, 'w', encoding='utf8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(data[row])

    def remove_jobs_in_filterlist(self, data: Dict[str, dict]):
        # load the filter-list if it exists, apply it to remove scraped jobs
        if data == {}:
            raise ValueError('No scraped job data to filter')

        if os.path.isfile(self.filterlist_path):
            self.filterlist = json.load(open(self.filterlist_path, 'r'))
            n_filtered = 0
            for jobid in self.filterlist:
                if jobid in data:
                    data.pop(jobid)
                    n_filtered += 1
            logging.info(f'removed {n_filtered} jobs present in filter-list')
        else:
            if hasattr(self, 'provider'):
                pass
            else:
                self.logger.warning(f'no jobs filtered, '
                                    f'missing {self.filterlist_path}')

    def remove_blacklisted_companies(self, data: Dict[str, dict]):
        # remove blacklisted companies from the scraped data
        # @TODO allow people to add companies to this via 'blacklist' status
        blacklist_ids = []
        for job_id, job_data in data.items():
            if job_data['company'] in self.blacklist:
                blacklist_ids.append(job_id)
        logging.info(f'removed {len(blacklist_ids)} jobs '
                     f'in blacklist from master-list')
        for job_id in blacklist_ids:
            data.pop(job_id)

    def update_filterjson(self):
        # parse master .csv file into an update for the filter-list json file
        if os.path.isfile(self.master_list_path):
            # load existing filtered jobs, if any
            if os.path.isfile(self.filterlist_path):
                filtered_jobs = json.load(open(self.filterlist_path, 'r'))
            else:
                filtered_jobs = {}

            # add jobs from csv that need to be filtered away, if any
            for job in self.read_csv(self.master_list_path, key_by_id=False):
                if job['status'] in REMOVE_STATUSES:
                    if job['id'] not in filtered_jobs:
                        logging.info('added {} to {}'.format(
                            job['id'], self.filterlist_path))
                    filtered_jobs[job['id']] = job

            # write out complete list with any additions from the masterlist
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

    def pre_filter(self, data: Dict[str, dict], provider):
        """function called by child classes that applies multiple filters
        before getting job blurbs"""
        # call date_filter if it is turned on
        if self.max_listing_days is not None:
            date_filter(data, self.max_listing_days)
        # call id_filter for master and duplicate lists, if they exist
        if os.path.isfile(self.master_list_path):
            id_filter(data, self.read_csv(self.master_list_path),
                      provider)
            if os.path.isfile(self.duplicate_list_path):
                id_filter(data, self.read_csv(
                    self.duplicate_list_path), provider)

        # filter out scraped jobs we have rejected, archived or blacklisted
        try:
            self.remove_jobs_in_filterlist(data)
        except ValueError:
            pass

        self.remove_blacklisted_companies(data)

    def delay_threader(self,
                       scrape_list: List[Dict], scrape_fn, parse_fn, threads):
        """function called by child classes to thread scrapes jobs
        with delays"""
        if not scrape_list:
            raise ValueError('No jobs to scrape')
        # calls delaying algorithm
        print("Calculating delay...")
        delays = delay_alg(len(scrape_list), self.delay_config)
        print("Done! Starting scrape!")
        # zips delays and scrape list as jobs for thread pool
        scrape_jobs = zip(scrape_list, delays)
        # start time recording
        start = time()
        # submits jobs and stores futures in dict
        results = {threads.submit(scrape_fn, job, delays): job['id']
                   for job, delays in scrape_jobs}

        # loops through futures and removes each if successfully parsed
        while results:
            # parses futures as they complete
            for future in as_completed(results):
                try:
                    job, html = future.result()
                    parse_fn(job, html)
                    del results[future]
                    del html
                except Exception as e:
                    self.logger.error(f'Blurb Future Error: {e}')
                    pass


        threads.shutdown()  # clean up threads when done
        # end and print recorded time
        end = time()
        print(f'{self.provider} scrape job took {(end - start):.3f}s')

    def update_masterlist(self):
        """use the scraped job listings to update the master spreadsheet"""
        if self.scrape_data == {}:
            raise ValueError('No scraped jobs, cannot update masterlist')

        # converts scrape data to ordered dictionary to filter all duplicates
        self.scrape_data = OrderedDict(sorted(self.scrape_data.items(),
                                              key=lambda t: t[1]['tags']))
        # filter out scraped jobs we have rejected, archived or blacklisted
        self.remove_jobs_in_filterlist(self.scrape_data)
        self.remove_blacklisted_companies(self.scrape_data)

        # load and update existing masterlist
        try:
            # open masterlist if it exists & init updated masterlist
            masterlist = self.read_csv(self.master_list_path)

            # update masterlist to remove filtered/blacklisted jobs
            self.remove_jobs_in_filterlist(masterlist)
            self.remove_blacklisted_companies(masterlist)

            # update masterlist to contain only new (unique) listings
            if self.save_dup:  # if true, saves duplicates to own file
                # calls tfidf filter and returns popped duplicate list
                duplicate_list = tfidf_filter(self.scrape_data, masterlist)

                logging.info(f'Saving {len(duplicate_list)} duplicates jobs to'
                             f' {self.duplicate_list_path}')
                # checks if duplicate list has entries
                if len(duplicate_list) > 0:
                    # checks if duplicate_list.csv exists
                    if os.path.isfile(self.duplicate_list_path):
                        # loads and adds current duplicates to list
                        master_dup = self.read_csv(self.duplicate_list_path)
                        master_dup.update(duplicate_list)
                        self.write_csv(data=master_dup,
                                       path=self.duplicate_list_path)
                    else:
                        # saves duplicates to duplicates_list.csv
                        self.write_csv(data=duplicate_list,
                                       path=self.duplicate_list_path)
            else:
                tfidf_filter(self.scrape_data, masterlist)

            masterlist.update(self.scrape_data)

            # save
            self.write_csv(data=masterlist, path=self.master_list_path)

        except FileNotFoundError:
            # run tfidf filter on initial scrape
            if self.save_dup:  # if true saves duplicates to own file
                duplicate_list = tfidf_filter(self.scrape_data)

                logging.info(
                    f'Saving {len(duplicate_list)} duplicates jobs to '
                    f'{self.duplicate_list_path}')

                if len(duplicate_list) > 0:
                    # saves duplicates to duplicates_list.csv
                    self.write_csv(data=duplicate_list,
                                   path=self.duplicate_list_path)

            else:
                tfidf_filter(self.scrape_data)

            # dump the results into the data folder as the masterlist
            self.write_csv(data=self.scrape_data, path=self.master_list_path)
            logging.info(
                f'no masterlist detected, added {len(self.scrape_data.keys())}'
                f' jobs to {self.master_list_path}')
