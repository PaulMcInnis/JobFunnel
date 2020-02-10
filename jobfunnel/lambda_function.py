
#Function which receives data from the SQS Queue
import sys
import os
from collections import defaultdict as dd
from typing import Union
import boto3
from jobfunnel import JobFunnel
from indeed import Indeed
from monster import Monster
from glassdoor import GlassDoor
from country_hash import *
from config import *
import pandas as pd 
from global_cache import * 
from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


PROVIDERS = {'indeed': Indeed, 'monster': Monster, 'glassdoor': GlassDoor}

providers_dict={
    0 : ['indeed', 'monster', 'glassdoor'],
    1: ['indeed', 'glassdoor']
}


data  = pd.read_csv('/Users/satyam/Desktop/data.csv')


df = pd.DataFrame(data)
df = df[['Company','Country']]

df.fillna('NA')



db = dd(dd)

for i in range(len(df)):
	key = df.iloc[i][0]
	coun = df.iloc[i][1]
	db[key][coun]=1

keyword = []
countries = []
for i in db.keys():
    for j in db[i].keys():
        keyword.append(i)
        countries.append(j)

#keyword = ['hackerrank']



def clean(kword):
    if ('.com Inc' in kword):
        kword = kword[:kword.index('.')+1]
    
    return kword




def lambda_handler(event,context):
    for i in range(len(keyword)):
        kword = keyword[i]
        ctry = countries[i]
        if(len(kword) < 5):
            continue
        kword = clean(kword)

        print('Keyword: ', kword)
        print('Country: ', ctry)
        if((kword not in glob_cache) and (ctry not in glob_cache[kword])):
            glob_cache[kword][ctry]=1
        else:
            continue
        if(ctry in ctry_hash):
            curr = 0
        else:
            curr = 1
            print('Country not supported by monster!')
        try:
            config =    {
                            'output_path': 'search',
                            'providers': providers_dict[curr],
                            'search_terms': {
                                                'region': {
                                                                'city': ctry, 
                                                                'country': ctry,
                                                                'radius': 25
                                                        },
                                                'keywords': [kword]
                                            }, 
                            'black_list': ['Infox Consulting'],
                            'log_level': 20, 
                            'similar': False,
                            'no_scrape': False,
                            'recover': False,
                            'save_duplicates': False,
                            'delay_config': {
                                                'function': 'linear',
                                                'delay': 10.0,
                                                'min_delay': 1.0,
                                                'random': False,
                                                'converge': False
                                            },
                            'data_path': 'search/data',
                            'master_list_path': 'search/{0}'.format(str(kword + '-' + ctry)),
                            'duplicate_list_path': 'search/duplicate_list.csv',
                            'filter_list_path': 'search/data/filter_list.json',
                            'log_path': 'search/data/jobfunnel.log', 'proxy': None
                        }
        # validate_config(config)
        except Exception as e:
            print(e)
            #print(e.strerror)
            sys.exit()

        # init class + logging
        jf = JobFunnel(config)
        jf.init_logging()

        # parse the master list path to update filter list
        jf.update_filterjson()

        # get jobs by either scraping jobs or loading dumped pickles
        if config['recover']:
            jf.load_pickles(config)
        elif config['no_scrape']:
            jf.load_pickle(config)
        else:
            for p in config['providers']:
                provider: Union[GlassDoor, Monster, Indeed] = PROVIDERS[p](config)
                provider_id = provider.__class__.__name__
                try:
                    #print('h
                    provider.scrape()
                    #print('hi2')
                    jf.scrape_data.update(provider.scrape_data)
                except Exception as e:
                    jf.logger.error(f'failed to scrape {provider_id}: {str(e)}')

            # dump scraped data to pickle
            jf.dump_pickle()

        # filter scraped data and dump to the masterlist file
        jf.update_masterlist()

        # done!
        jf.logger.info(
            "done. see un-archived jobs in " + config['master_list_path'])
        print('-'*100)


'''s3 = boto3.client('s3')
s3.upload_file(config['master_list_path'], S3_BUCKET_NAME, 'master_list.csv')
os.system("ls /tmp/")'''

creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
if os.path.exists(''):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

    
lambda_handler(1,1)





    