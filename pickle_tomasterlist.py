import pickle
import json
import io
from datetime import date
import pandas as pd
import logging

MASTERLIST_FILEPATH = 'jobs_masterlist.xlsx'
FILTERLIST_FILEPATH = 'filterlist.json'
LOG_FILEPATH = 'jobpy.log'
LOG_LEVEL = logging.INFO

# @TODO add a filter that looks for listings that contain certain keywords
# @TODO add some methods to add 'attractiveness' metric obtained from keyword hits
# @TODO add bigdata style analysis/viewer

# current date
date_text = date.today().strftime("%Y-%m-%d")

# setup logging
logging.basicConfig(filename=LOG_FILEPATH,level=LOG_LEVEL)
logging.info('jobpy pickle_tomasterlist running @ : ' + date_text)

# Python 2+3 unicode json
try:
    to_unicode = unicode
except NameError:
    to_unicode = str

# open the daily pickle file --> dict if it exists
try:
    pickle_filepath = 'jobs_' + date_text + '.pkl'
    with open(pickle_filepath, 'rb') as pickle_file:
        dailyjobdict = pickle.load(pickle_file)
except FileNotFoundError:
    logging.error(pickle_filepath + ' not found!')
    raise FileNotFoundError

# load the filterlist if it exists, and apply it to remove any filtered jobs
try:
    with open(FILTERLIST_FILEPATH) as filter_file:
        json_filter_list = json.load(filter_file)
    # pop jobs out of the dailyjobdict that are on the filterlist
    # @TODO pop jobs that are expired 'no longer available'
    for jobid in json_filter_list:
        dailyjobdict.pop(jobid, None)
        logging.debug ('job: ' + jobid + ' in filterlist.json, not added to masterlist')

except FileNotFoundError:
    logging.warning ('filterlist.json not found!, no filtration!')

try:
    # open master list if it exists
    masterlist = pd.read_excel(MASTERLIST_FILEPATH)
    masterlist = masterlist.T
    # add master list id's to a list
    masterlist_ids = masterlist.columns.tolist()
    # make a new output dict for the updated masterlist
    newmasterlist_dict = {}

    # identify the new job id's not already in master list or in filterlist
    # currently dailyjob dict has nothing from filterlist in it but has jobs already in masterlist
    for jobid in dailyjobdict:
        # catch daily only mode
        if dailyjobdict[jobid]['state'] != 'filtered':
            # make a copy for output
            output_job_dict = dailyjobdict[jobid]
            # preserve existing state in output (may be user-set in masterlist excel)
            try:
                existingstate = masterlist[jobid]['state']
                output_job_dict.update({'state' : existingstate})
                #print ('existing job ' +jobid + ' already in masterlist, state preserved')
            except KeyError:
                logging.debug ('jobid ' + jobid + ' not in existing masterlist')

            # make sure new jobs have correct state
            if jobid not in masterlist_ids and jobid not in json_filter_list:
                # change state to new
                output_job_dict.update({'state' : 'new'})
                logging.info ('job ' + jobid + ' has been added to the masterlist')

            # make the url clickable in excel
            output_job_dict.update({'link': '=HYPERLINK("' + str(output_job_dict['link']) + '")'})

            # add current job to output
            newmasterlist_dict.update({jobid : output_job_dict})

    # save the output to excel again
    #save a XLSX 2010 of jobs dict transposed (vertically)
    df = pd.DataFrame(newmasterlist_dict)
    df = df.T
    df.to_excel(MASTERLIST_FILEPATH)

except FileNotFoundError:
    #@TODO logging
    logging.info ("no masterlist detected, adding all daily jobs to " + MASTERLIST_FILEPATH)

    # dump the results into the out folder as the masterlist
    df = pd.DataFrame(dailyjobdict)
    df = df.T
    df.to_excel(MASTERLIST_FILEPATH)


