
import bs4
import numpy
import requests
import pickle
import itertools
import yaml
import re
import pandas as pd
from datetime import date

JOB = "Engineer"
REGION = "Waterloo%2C+ON&radius=25"
URL_BASE = 'http://www.indeed.ca'
RESULTS_PER_PAGE = 50 # max seems to be 50 per page load
BS4_PARSER = 'lxml'

# current date
date_text = date.today().strftime("%Y-%m-%d")

# custom exception indicating possible regex issues (need to update?)
class IDSearchException(Exception):
    pass

# search url, 50 results per page
url_search = URL_BASE + '/jobs?q=' + JOB + '&l=' + REGION + '&limit=' + str(RESULTS_PER_PAGE)

# get the HTML data, initialize bs4 with lxml
request_HTML = requests.get(url_search)
soup_base = bs4.BeautifulSoup(request_HTML.text, BS4_PARSER)

# find total number of results @TODO make cleaner
num_results = soup_base.find(id = 'searchCount').contents[0].split()[-1]
num_results = int(re.sub("[^0-9]","", num_results))

# find total number of pages @TODO implement a logger
num_pages = int(numpy.ceil(num_results/RESULTS_PER_PAGE))
print('Found ' + str(num_results) + ' results over ' + str(num_pages) + ' pages '
               + str(RESULTS_PER_PAGE) + ' listings/page) \n')

# generate the page urls, save as a list
list_of_page_urls = []
for page in range(0, num_pages):
    url_page = url_search +  '&start=' + str(page*RESULTS_PER_PAGE)
    list_of_page_urls.append(url_page)

# scrape soups of all listed jobs pages
list_of_job_soups_by_page = []
for page in range(len(list_of_page_urls)):
    print('getting page ' + str(page) + ': ' + list_of_page_urls[page])
    html_page = requests.get(list_of_page_urls[page])
    soup_page = bs4.BeautifulSoup(html_page.text, BS4_PARSER)
    # process page's soup to obtain list of all jobs only
    jobs_page = soup_page.find_all('div', attrs={'data-tn-component': 'organicJob'})
    list_of_job_soups_by_page.append(jobs_page)

# flatten the 2D list so that each list item is a separate job
list_of_job_soups = sum(list_of_job_soups_by_page, [])

# make a dict of job postings
dict_of_job_dicts =  {}
for job in list_of_job_soups:
    #@TODO filter out sponsored listings on line 45?
    # find the relevant listing data
    title = job.find('a', attrs={'data-tn-element': "jobTitle"}).text.strip()
    company = job.find('span', attrs={"itemprop":"name"}).text.strip()
    salary_result = job.find('nobr')
    location = job.find('span', {'class': 'location'}).text.strip()
    description = job.find_all('div')[0].text.strip()
    #@TODO try and get the date posted into a good format
    # make a unique key with save job URL
    try:
        # get savejob link sl resultLink save-job-link
        stt = job.find_all('a', { "class" : "sl resultLink save-job-link "})
        job_key = re.findall('id=\"sj_(.*)\" onclick', str(stt))[0]
        link = URL_BASE + '/viewjob?jk=' + job_key
    except IndexError:
        raise IDSearchException('unable to extract job id from posting ' + company + ' ' + title)
    #add extra salary info if listed
    if salary_result:
        salary = salary_result.text.strip()
    # append data as a dict to dict of jobs
    job_dict = {'title' : title, 'job' : company, 'location' : location, 'description' : description, 'link' : link, 'state' : 'daily', 'date' : date_text}
    #append salary if it exists
    if salary_result:
        job_dict.update({'salary' : salary})
    #add the job to the dict
    dict_of_job_dicts.update({str(job_key) : job_dict})


# save the resulting jobs dict as a pickle file
with open('jobs_' + date_text + '.pkl', 'wb') as pickle_file:
    pickle.dump(dict_of_job_dicts, pickle_file)
