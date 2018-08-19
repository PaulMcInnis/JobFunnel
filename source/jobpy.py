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

    """class to scrape data off of indeed.ca, with xlsx-based I/O"""

    def __init__(self, args):
        # paths
        self.masterlist = args['MASTERLIST_PATH']
        self.filterlist = args['FILTERLIST_PATH']
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
        ## parse master .xlsx file into an update for the filter-list .json file

        filter_list = []
        try:
            # add jobs the user wants to filter away
            new_filter_list = []
            for job in self.read_csv(self.masterlist):
                try:
                    if (job['status'] == 'archive'):
                        new_filter_list.append(job.name)
                except TypeError:
                    logging.warning ('job={0} appears malformed!'
                        'unable to add to filter list!'.format(job))

            # if there are new jobs to add to the filter
            if len(new_filter_list) > 0:
                # load the existing filterlist.json
                existing_filter_list = []
                try:
                    # open the filter list JSON
                    with open(self.filterlist) as filter_file:
                        existing_filter_list = json.load(filter_file)

                    # make a list of only  entries not in the filterlist
                    new_filter_entries = []
                    for jobid in new_filter_list:
                        if jobid not in existing_filter_list:
                            new_filter_entries.append(jobid)

                    # extend the existing filter list
                    filter_list = new_filter_entries + existing_filter_list
                    logging.info ('appended {0} jobids to {1}'.format(
                        len(new_filter_entries), self.filterlist))

                except IOError:
                    # assume that this is a fresh filter list
                    filter_list = new_filter_list
                    logging.info ('appended {0} jobids to {1}'.format(
                        len(filter_list), self.filterlist))

                # write out the complete list with any additions from the masterlist
                with open(self.filterlist, 'w', encoding='utf8') as outfile:
                    str_ = json.dumps(filter_list,
                                      indent=4,
                                      sort_keys=True,
                                      separators=(',', ': '),
                                      ensure_ascii=False)
                    outfile.write(self.encoding(str_))

        except IOError:
            logging.error ("no master-list detected to load filters from," \
                           " no changes to filter-list made")

    def scrape_indeed_to_pickle(self):
        ## scrape a page of indeed results to a pickle
        # setup logging
        logging.basicConfig(filename=self.logfile,level=logging.INFO)
        logging.info('jobpy indeed_topickle running @ : ' + self.date_string)

        # form the query string
        for i, s in enumerate(self.search_terms['keywords']):
            if i == 0: query = s
            else: query += '+' + s
        logging.info('query string = ' + query)

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
        logging.info ('Found {0} results)'.format(num_results))

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
        jobs =  {}
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
            jobs.update({str(job['id']) : job})

        # set the current dict
        self.daily_scrape_dict = jobs

        # save the resulting jobs dict as a pickle file
        pickle_name = 'jobs_{0}.pkl'.format(self.date_string)
        pickle.dump(jobs, open(os.path.join(self.pickles_dir,pickle_name), 'wb'))
        logging.info('pickle file successfully dumped to ' + pickle_name)


    def pickle_to_masterlist(self):
        ## use the scraped job listings to update the master spreadsheet
        # try to load it from set var first:
        if self.daily_scrape_dict:
            dailyjobdict = self.daily_scrape_dict
        else:
            # try to open the daily pickle file --> dict if it exists
            try:
                pickle_filepath = os.path.join('data', 'scraped', 'jobs_{0}.pkl'.format(
                    self.date_string))
                with open(pickle_filepath, 'rb') as pickle_file:
                    dailyjobdict = pickle.load(pickle_file)
            except FileNotFoundError as e:
                logging.error(pickle_filepath + ' not found!')
                raise e

        # load the filterlist if it exists, and apply it to remove any filtered jobs
        try:
            with open(self.filterlist) as filter_file:
                json_filter_list = json.load(filter_file)
            # pop jobs out of the dailyjobdict that are on the filterlist
            # @TODO pop jobs that are expired 'no longer available'
            for jobid in json_filter_list:
                dailyjobdict.pop(jobid, None)
                logging.debug ('job: {0} present in filter-list, not added '
                    'to master-list'.format(jobid))
        except FileNotFoundError:
            logging.warning ('filterlist.json not found!, no filtration!')
            json_filter_list = []

        try:
            # open master list if it exists & init updated master-list
            masterlist = self.read_csv(self.masterlist)
            newmasterlist_dict = {}

            # identify the new job id's not in master list or in filter-list
            for jobid in dailyjobdict:
                job = dailyjobdict[jobid]
                # catch daily only jobs
                if job['status'] != 'filtered':
                    # preserve user state
                    try:
                        job['status'] = masterlist[jobid]['status']
                    except KeyError:
                        logging.debug('jobid {0} not in master-list'.format(jobid))

                    # make sure new jobs have correct state
                    if jobid not in masterlist and jobid not in json_filter_list:
                        # change state to new
                        job['status'] = 'new'
                        logging.info ('job : {0} added to masterlist'.format(jobid))

                    # add current job to output
                    newmasterlist_dict.update({jobid : job})
            # save
            self.write_csv(data=newmasterlist_dict, path=self.masterlist)

        except FileNotFoundError:
            logging.info ('no masterlist detected, adding all'
                ' daily jobs to {0}'.format(self.masterlist))

            # dump the results into the out folder as the master-list
            self.write_csv(data=dailyjobdict, path=self.masterlist)
