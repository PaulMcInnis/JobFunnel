import pickle
import pprint
import json
import io
from datetime import date
import pandas as pd

MASTERLIST_FILEPATH = 'out/jobs_masterlist.xlsx'
FILTERLIST_FILEPATH = 'filterlist.json'

# @TODO add a filter that looks for listings that contain certain keywords
# @TODO add some methods to add 'attractiveness' metric obtained from keyword hits
# @TODO add bigdata style analysis/viewer

#current date
date_text = date.today().strftime("%Y-%m-%d")

# Python 2+3 unicode json
try:
    to_unicode = unicode
except NameError:
    to_unicode = str

# open the daily pickle file --> dict
with open('jobs_' + date_text + '.pkl', 'rb') as pickle_file:
    dailyjobdict = pickle.load(pickle_file)

# if the user has set jobs to filtered, add them to the filterlist/create a new one @TODO bug doesnt preserve states
filter_list = []
try:
    # open the masterlist file
    df = pd.read_excel(MASTERLIST_FILEPATH)
    df = df.T
    # add to filterlist if user set anything to filtered
    new_filter_list = []
    for job in df:
        if (df[job]['state'] == 'filtered'):
            new_filter_list.append(df[job].name)

    # if there are new jobs to add to the filter
    if len(new_filter_list) > 0:
        # open existing filterlist.json
        existing_filter_list = []
        try:
            with open(FILTERLIST_FILEPATH) as filter_file:
                existing_filter_list = json.load(filter_file)
            # make a list that only adds new entries
            new_filter_entries = []
            for jobid in new_filter_list:
                if jobid not in existing_filter_list:
                    new_filter_entries.append(jobid)
            filter_list = new_filter_entries + existing_filter_list
            print ('appended ' + str(len(new_filter_entries)) + ' jobids to ' + FILTERLIST_FILEPATH)

        except FileNotFoundError:
            print ('no ' + FILTERLIST_FILEPATH + ' filter found, appended ' + str(len(new_filter_entries)) + ' jobids to ' + FILTERLIST_FILEPATH)
            filter_list = new_filter_list

        # write out the complete list with any additions from the masterlist
        with io.open(FILTERLIST_FILEPATH, 'w', encoding='utf8') as outfile:
            str_ = json.dumps(filter_list, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
            outfile.write(to_unicode(str_))

except FileNotFoundError:
    print ("no masterlist detected to load filters from")

# load the filterlist if it exists, and apply it to remove any filtered jobs
try:
    with open(FILTERLIST_FILEPATH) as filter_file:
        json_filter_list = json.load(filter_file)
    # pop jobs out of the dailyjobdict that are on the filterlist
    # @TODO pop jobs that are expired 'no longer available'
    for jobid in json_filter_list:
        dailyjobdict.pop(jobid, None)
        #print ('job: ' + jobid + ' in filterlist.json, not added to masterlist')

except FileNotFoundError:
    print ('filterlist.json not found, no filtration')

#NOTE: NO STATE=FILTERED JOBS SHOULD BE POSSIBLE PAST THIS POINT

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
        # make a copy for output
        output_job_dict = dailyjobdict[jobid]
        # preserve existing state in output (may be user-set in masterlist excel)
        try:
            existingstate = masterlist[jobid]['state']
            output_job_dict.update({'state' : existingstate})
            #print ('existing job ' +jobid + ' already in masterlist, state preserved')
        except KeyError:
            print ('unable to open masterlist jobid ' + jobid)

        # make sure new jobs have correct state
        if jobid not in masterlist_ids and jobid not in filter_list:
            print ('job ' + jobid + ' IS NEW')
            # change state to new
            output_job_dict.update({'state' : 'new'})

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
    print("no masterlist detected, adding all daily jobs to " + MASTERLIST_FILEPATH)

    # dump the results into the out folder as the masterlist
    df = pd.DataFrame(dailyjobdict)
    df = df.T
    df.to_excel(MASTERLIST_FILEPATH)
