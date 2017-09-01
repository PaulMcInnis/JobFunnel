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

# if the user has set jobs to filtered, add them to the filterlist/create a new one @TODO bug doesnt preserve states
filter_list = []
try:
    # open the masterlist file
    df = pd.read_excel(MASTERLIST_FILEPATH)
    df = df.T

    # add to filterlist if user set anything to filtered
    new_filter_list = []
    for job in df:
        try:
            if (df[job]['state'] == 'filtered'):
                new_filter_list.append(df[job].name)
        except TypeError:
            logging.warning ('job id malformed!, unable to add to list!')

    # if there are new jobs to add to the filter
    if len(new_filter_list) > 0:
        # open existing filterlist.json
        try:
            existing_filter_list = []

            # open the filter list JSON
            with open(FILTERLIST_FILEPATH) as filter_file:
                existing_filter_list = json.load(filter_file)

            new_filter_entries = []

            # make a list of only new entries that are not in the filterlist
            for jobid in new_filter_list:
                if jobid not in existing_filter_list:
                    new_filter_entries.append(jobid)

            # extend the existing filter list
            filter_list = new_filter_entries + existing_filter_list
            logging.info ('appended ' + str(len(new_filter_entries)) +
                            ' jobids to ' + FILTERLIST_FILEPATH)

        except FileNotFoundError:
            # make a list of entires to add from the masterlist, creating a filterlist
            filter_list = new_filter_list
            logging.info ('appended ' + str(len(filter_list)) +
                            ' jobids to a new filterlist ' + FILTERLIST_FILEPATH)

        # write out the complete list with any additions from the masterlist
        with io.open(FILTERLIST_FILEPATH, 'w', encoding='utf8') as outfile:
            str_ = json.dumps(filter_list, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
            outfile.write(to_unicode(str_))

except FileNotFoundError:
    logging.error ("no masterlist detected to load filters from, no changes to filterlist made")
