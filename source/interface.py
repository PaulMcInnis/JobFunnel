## Paul McInnis 2018
## scrapes data off indeed.ca, pickles it, and applies search filters

import sys
import pickle
import json
import logging
import argparse
import pdb; pdb.set_trace()
import pandas as pd
from datetime import date
from config import default_args

class jobpy(object):

    """class to scrape data off of indeed.ca, with xlsx-based I/O"""

    def __init__(self, args):
        # paths
        self.masterlist = args['MASTERLIST_PATH']
        self.filterlist = args['FILTERLIST_PATH']
        self.logfile = args['LOG_PATH']

        # other inits
        self.similar_results = args['SIMILAR']
        self.bs4_parser = args['BS4_PARSER']
        self.results_per_page = args['RESULTS_PER_PAGE']

        # date string for pickle files
        self.date_string = date.today().strftime("%Y-%m-%d")

        # search term configuration data #@TODO support python3 encoding
        self.search_terms = json.load(open(args['SEARCHTERMS_PATH'], 'rb'))

        # logging
        logging.basicConfig(filename=args['LOG_PATH'], level=args['LOG_LEVEL'])
        logging.info('jobpy initialized at {0}'.format(self.date_string))

        # handle Python 2 & 3 Unicode formatting
        try:
            self.encoding = unicode
        except NameError: # @TODO use sys.version_info instead
            self.encoding = str


    def masterlist_to_filterjson(self):
        ## parse master .xlsx file into an update for the filter-list .json file
        # @TODO return changes?

        filter_list = []
        try:
            # read the master-list
            df = pd.read_excel(self.masterlist).T

            # add jobs user set state='filtered' to the filter-list json
            new_filter_list = []
            for job in df:
                try:
                    if (df[job]['state'] == 'filtered'):
                        new_filter_list.append(df[job].name)
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

                except FileNotFoundError:
                    # assume that this is a fresh filter list
                    # @TODO some sort of prompt?
                    filter_list = new_filter_list
                    logging.info ('appended {0} jobids to {1}'.format(
                        len(filter_list), self.filterlist))

                # write out the complete list with any additions from the masterlist
                with io.open(self.filterlist, 'w', encoding='utf8') as outfile:
                    str_ = json.dumps(filter_list,
                                      indent=4,
                                      sort_keys=True,
                                      separators=(',', ': '),
                                      ensure_ascii=False)
                    outfile.write(self.encoding(str_))

        except FileNotFoundError:
            logging.error ("no master-list detected to load filters from,"
                           " no changes to filter-list made")

    def scrape_indeed_to_pickle(self):
        ## scrape a page of indeed results to a pickle
        # init http strings
        search_string = "{0}%2C+{1}&radius={2}".format(
            self.search_terms['region']['city'],
            self.search_terms['region']['province'],
            self.search_terms['region']['radius'],
        )
        url_base = 'http://www.indeed.{0}'.format(
            self.search_terms['region']['domain'])

        # setup logging
        logging.basicConfig(filename=self.logfile,level=logging.INFO)
        logging.info('jobpy indeed_topickle running @ : ' + self.date_string)

        # search url, 50 results per page #@TODO support more than 1 search term
        url_search = '{0}/jobs?q={1}&l={2}&limit={3}&filter={4}'.format(
            url_base, self.search_terms['search'][0], search_string,
            self.results_per_page, int(self.similar_results))

        # get the HTML data, initialize bs4 with lxml
        request_HTML = requests.get(url_search)
        soup_base = bs4.BeautifulSoup(request_HTML.text, self.bs4_parser)

        # find total number of results @TODO make cleaner`
        num_results = soup_base.find(id = 'searchCount').contents[0].split()[-1]
        num_results = int(re.sub("[^0-9]","", num_results))

        # find total number of pages @TODO implement a logger
        num_pages = int(numpy.ceil(num_results/self.results_per_page))
        logging.info ('Found {0} results over {1} pages ({2}/page)\n'.format(
            num_results, num_pages, self.results_per_page))

        # generate the page urls, save as a list
        list_of_page_urls = []
        for page in range(0, num_pages):
            url_page = '{0}&start={1}'.format(
                url_search, page*self.results_per_page)
            list_of_page_urls.append(url_page)

        # scrape soups of all listed jobs pages
        list_of_job_soups_by_page = []
        for page in range(len(list_of_page_urls)):
            # log current scraped page
            logging.info ('getting page {0} : {1}'.format(
                page, list_of_page_urls[page]))

            # init a bs4 object containing the page
            html_page = requests.get(list_of_page_urls[page])
            soup_page = bs4.BeautifulSoup(html_page.text, self.bs4_parser)

            # process page's soup to obtain list of all jobs only
            jobs_page = soup_page.find_all('div',
                attrs={'data-tn-component': 'organicJob'})
            list_of_job_soups_by_page.append(jobs_page)

        # flatten the 2D list so that each list item is a separate job
        list_of_job_soups = sum(list_of_job_soups_by_page, [])

        # make a dict of job postings from the listings
        dict_of_job_dicts =  {}
        for job in list_of_job_soups:

            # if it's been posted days ago don't set it to new!!
            information = job.find("div", class_="result-link-bar")
            if (len(re.findall(r'days ago', str(information))) > 0):
                state = 'filtered'
            else:
                state = 'daily'

            # scrape the actual posting data
            title = job.find('a',
                attrs={'data-tn-element': "jobTitle"}).text.strip()
            company = job.find('span', attrs={"itemprop":"name"}).text.strip()
            salary_result = job.find('nobr')
            location = job.find('span', {'class': 'location'}).text.strip()
            description = job.find_all('div')[0].text.strip()
            #@TODO try and get the date posted into a good format

            # custom exception to indicate possible regex issues
            class IDSearchException(Exception):
                pass

            # make a unique job id key with the 'save job' URL
            try:
                # get savejob link sl resultLink save-job-link
                stt = job.find_all('a',
                    { "class" : "sl resultLink save-job-link "})
                job_key = re.findall('id=\"sj_(.*)\" onclick', str(stt))[0]
                link = '{0}/viewjob?jk={1}'.format(url_base, job_key)
            except IndexError:
                error_text = 'regex issue! unable to scrape job id from' \
                    ' posting {0} {1}'.format(company, title)
                logging.error(error_text)
                raise IDSearchException(error_text)

            # append data to running dict() of all scraped jobs
            job_dict = {'title'         : title,
                        'job'           : company,
                        'location'      : location,
                        'description'   : description,
                        'link'          : link,
                        'state'         : state,
                        'date'          : date_string}

            # append salary if it exists
            if salary_result: job_dict.update(
                {'salary' : salary_result.text.strip()})

            # add the job to the dict
            dict_of_job_dicts.update({str(job_key) : job_dict})

        # save the resulting jobs dict as a pickle file
        pickle_filepath = 'jobs_{0}.pkl'.format(self.date_string)
        with open(pickle_filepath, 'wb') as pickle_file:
            pickle.dump(dict_of_job_dicts, pickle_file)

        logging.info('pickle file successfully dumped to ' + pickle_filepath)


    def pickle_to_masterlist(self):
        ## use the scraped job listings to update the master spreadsheet
        # open the daily pickle file --> dict if it exists
        try:
            pickle_filepath = 'jobs_{0}.pkl'.format(self.date_string)
            with open(pickle_filepath, 'rb') as pickle_file:
                dailyjobdict = pickle.load(pickle_file)
        except FileNotFoundError:
            logging.error(pickle_filepath + ' not found!')
            raise FileNotFoundError

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

        try:
            # open master list if it exists
            masterlist = pd.read_excel(self.masterlist)
            masterlist = masterlist.T

            # add master list id's to a list, init updated master-list
            masterlist_ids = masterlist.columns.tolist()
            newmasterlist_dict = {}

            # identify the new job id's not in master list or in filter-list
            for jobid in dailyjobdict:
                # catch daily only jobs
                if dailyjobdict[jobid]['state'] != 'filtered':
                    # preserve user state
                    output_job_dict = dailyjobdict[jobid]
                    try:
                        existingstate = masterlist[jobid]['state']
                        output_job_dict.update({'state' : existingstate})
                    except KeyError:
                        logging.debug('jobid {0} not in master-list'.format(
                            jobid))

                    # make sure new jobs have correct state
                    if jobid not in masterlist_ids and \
                       jobid not in json_filter_list:
                        # change state to new
                        output_job_dict.update({'state' : 'new'})
                        logging.info ('job : {0} has been added to the '
                            'masterlist'.format(jobid))

                    # make the url clickable in excel
                    output_job_dict.update({'link': '=HYPERLINK("{0}")'.format(
                        output_job_dict['link'])})

                    # add current job to output
                    newmasterlist_dict.update({jobid : output_job_dict})

            # save the output to excel again
            #save a XLSX 2010 of jobs dict() transposed (vertically)
            df = pd.DataFrame(newmasterlist_dict)
            df = df.T
            df.to_excel(self.masterlist)

        except FileNotFoundError:
            logging.info ('no masterlist detected, adding all'
                ' daily jobs to {0}'.format(self.masterlist))

            # dump the results into the out folder as the master-list
            df = pd.DataFrame(dailyjobdict)
            df = df.T
            df.to_excel(self.masterlist)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', dest='masterlist_path', action='store',
        required=False, default=default_args['MASTERLIST_PATH'],
        help='path to a .xlsx spreadsheet file used to view and filter jobs'
             ' one will be created if one does not exist at location specified')
    parser.add_argument('-f', dest='filterlist_path', action='store',
        required=False, default=default_args['FILTERLIST_PATH'],
        help='path to a .json file which contains jobs rejected from the .xlsx'
             ' one will be created if one does not exist at location specified')
    parser.add_argument('-t', dest='searchterms_path', action='store',
        required=False, default=default_args['SEARCHTERMS_PATH'],
        help='path to a .json file which contains the desired search config'
             ' one will be created if one does not exist at location specified')
    parser.add_argument('--similar', dest='similar', action='store_true',
        help='set to true to get \'similar\'job listings on indeed')

    args = vars(parser.parse_args(sys.argv[1:]))

    # some more defaults not set by argparse rn:
    args.update({'LOG_PATH'         : default_args['LOG_PATH'],
                 'BS4_PARSER'       : default_args['BS4_PARSER'],
                 'RESULTS_PER_PAGE' : default_args['RESULTS_PER_PAGE'],
                 })

    # init class
    jobpy_interface = jobpy(args)

    # parse the xslx to filter list, scrape new listings & add to master xslx
    jobpy_interface.masterlist_to_filterjson()
    jobpy_interface.scrape_indeed_to_pickle()
    jobpy_interface.pickle_tomasterlist()

    print "done"
