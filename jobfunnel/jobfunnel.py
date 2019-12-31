## Paul McInnis 2018
## writes pickles to master list path and applies search filters

import csv
import json
import logging
import os
import pickle
import random
import re

from datetime import date
from typing import Dict, List
from concurrent.futures import as_completed

from .tools.filters import tfidf_filter, id_filter
from .tools.delay import random_delay

# setting job status to these words removes them from masterlist + adds to
# blacklist
REMOVE_STATUSES = ['archive', 'archived', 'remove', 'rejected']

# csv header:
MASTERLIST_HEADER = ['status', 'title', 'company', 'location', 'date', 'blurb',
                     'link', 'id', 'provider']

# user agent list
# https://developers.whatismybrowser.com/useragents/explore/
user_agent_list = [
    # chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/44.0.2403.157 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, '
    'like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    # firefox
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like '
    'Gecko',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET '
    'CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
]


class JobFunnel(object):
    """class that writes pickles to master list path and applies search
    filters """

    def __init__(self, args):
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
        self.user_agent = random.choice(user_agent_list)

        # date string for pickle files
        self.date_string = date.today().strftime("%Y-%m-%d")

        # search term configuration data
        self.search_terms = args['search_terms']

        # Set delay settings if they exist
        self.delay_config = None
        if args['delay_config'] is not None:
            self.delay_config = args['delay_config']

        # create data dir
        if not os.path.exists(args['data_path']):
            os.makedirs(args['data_path'])

    def init_logging(self):
        # initialise logging to file
        self.logger = logging.getLogger()
        self.logger.setLevel(self.loglevel)
        logging.basicConfig(filename=self.logfile, level=self.loglevel)
        logging.getLogger().addHandler(logging.StreamHandler())
        self.logger.info(f'jobfunnel initialized at {self.date_string}')

    def scrape(self):
        """function to be implemented by child classes"""
        raise NotImplementedError()

    def load_pickle(self, args):
        """function to load today's daily scrape pickle"""
        ## only to be used in no_scrape mode
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
        ## only to be used in recovery mode
        pickle_found = False
        pickle_path = os.path.join(args['data_path'])
        for root, dirs, files in os.walk(pickle_path):
            for file in files:
                if re.findall(r'jobs_.*', file):
                    if not pickle_found: pickle_found = True
                    pickle_file = file
                    pickle_filepath = os.path.join(pickle_path, pickle_file)
                    logging.info(f'loading pickle file: {pickle_filepath}')
                    self.scrape_data.update(
                        pickle.load(open(pickle_filepath, 'rb')))
        if not pickle_found:
            logging.error(f'no pickles found in {pickle_path}! Have you '
                          f'scraped any jobs?')
            raise e

    def dump_pickle(self):
        """function to dump a pickle of the daily scrape dict"""
        pickle_name = f'jobs_{self.date_string}.pkl'
        pickle.dump(self.scrape_data,
                    open(os.path.join(self.pickles_dir, pickle_name), 'wb'))

    def read_csv(self, path, key_by_id=True):
        ## reads csv passed in as path
        with open(path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            if key_by_id:
                return dict([(j['id'], j) for j in reader])
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
            logging.info(f'removed {n_filtered} jobs present in filter-list')
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
            f'removed {len(blacklist_ids)} jobs in black-list from '
            f'master-list')
        for job_id in blacklist_ids:
            data.pop(job_id)

    def update_filterjson(self):
        ## parse master .csv file into an update for the filter-list .json file
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

    def pre_filter(self, scrape_data: Dict[str, dict], provider):
        """
        Function called by child classes that applies multiple filters
        before getting job blurbs
        """
        # Call id_filter for master and duplicate lists, if they exist
        if os.path.isfile(self.master_list_path):
            id_filter(scrape_data, self.read_csv(self.master_list_path),
                      provider)
            if os.path.isfile(self.duplicate_list_path):
                id_filter(scrape_data, self.read_csv(
                    self.duplicate_list_path), provider)

        # filter out scraped jobs we have rejected, archived or blacklisted

        try:
            self.remove_jobs_in_filterlist(scrape_data)
        except ValueError:
            pass
        self.remove_blacklisted_companies(scrape_data)

    def delay_threader(self,
                       scrape_list: List[Dict], scrape_fn, parse_fn, threads):
        """
        Function called by child classes to thread scrapes jobs with delays
        """
        if not scrape_list:
            raise ValueError("No scraped jobs returned")
        delays = random_delay(len(scrape_list), self.delay_config)
        # Zips delays and scrape list as jobs for thread pool
        scrape_jobs = zip(scrape_list, delays)

        # Ballpark estimate of scrape time
        logging.info("Scrape time estimated to take {} s or "
                     "greater ".format(round((sum(delays) / 8) + 1, 2)))

        # Submits jobs and stores futures in dict
        results = {threads.submit(scrape_fn, job, delays): job['id']
                   for job, delays in scrape_jobs}
        # Loops through futures and removes each if successfully parsed
        while results:
            # Gets each future as they complete
            for future in as_completed(results):
                try:
                    job, html = future.result()
                    parse_fn(job, html)
                except Exception:
                    pass
                del results[future]
        threads.shutdown()

    def update_masterlist(self):
        ## use the scraped job listings to update the master spreadsheet
        if self.scrape_data == {}:
            raise ValueError("No scraped jobs, cannot update masterlist")

        # filter out scraped jobs we have rejected, archived or blacklisted
        ## Left this here in case of pickle loading
        self.remove_jobs_in_filterlist(self.scrape_data)
        self.remove_blacklisted_companies(self.scrape_data)

        # load and update existing masterlist
        try:
            # open master list if it exists & init updated master-list
            masterlist = self.read_csv(self.master_list_path)

            # update masterlist to remove filtered/blacklisted jobs
            self.remove_jobs_in_filterlist(masterlist)
            self.remove_blacklisted_companies(masterlist)

            # update masterlist to contain only new (unique) listings
            if self.save_dup:  # if true, saves duplicates to own file
                # Calls tf_idf filter and returns popped duplicate list
                duplicate_list = tfidf_filter(self.scrape_data, masterlist)

                logging.info(f'Saving {len(duplicate_list)} duplicates jobs to'
                             f' {self.duplicate_list_path}')
                # Checks if duplicate list has entries
                if len(duplicate_list) > 0:
                    # Checks if duplicate_list.csv exists
                    if os.path.isfile(self.duplicate_list_path):
                        # Loads and adds current duplicates to list
                        master_dup = self.read_csv(self.duplicate_list_path)
                        master_dup.update(duplicate_list)
                        self.write_csv(data=master_dup,
                                       path=self.duplicate_list_path)
                    else:
                        # Saves duplicates to duplicates_list.csv
                        self.write_csv(data=duplicate_list,
                                       path=self.duplicate_list_path)
            else:
                tfidf_filter(self.scrape_data, masterlist)

            masterlist.update(self.scrape_data)

            # save
            self.write_csv(data=masterlist, path=self.master_list_path)

        except FileNotFoundError:
            # Run tf_idf filter on initial scrape
            if self.save_dup:  # if true saves duplicates to own file
                duplicate_list = tfidf_filter(self.scrape_data)

                logging.info(
                    f'Saving {len(duplicate_list)} duplicates jobs to '
                    f'{self.duplicate_list_path}')

                if len(duplicate_list) > 0:
                    # Saves duplicates to duplicates_list.csv
                    self.write_csv(data=duplicate_list,
                                   path=self.duplicate_list_path)
            else:
                tfidf_filter(self.scrape_data)

            # dump the results into the data folder as the master-list
            self.write_csv(data=self.scrape_data, path=self.master_list_path)
            logging.info(
                f'no masterlist detected, added {len(self.scrape_data.keys())}'
                f' jobs to {self.master_list_path}')
