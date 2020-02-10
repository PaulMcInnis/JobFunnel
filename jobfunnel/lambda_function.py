#Function which receives data from the SQS Queue
import sys
import os
from collections import defaultdict as dd
from typing import Union
#import boto3
from jobfunnel import JobFunnel
from indeed import Indeed
from monster import Monster
from glassdoor import GlassDoor
from country_hash import *
from config import *
import pandas as pd 
from global_cache import * 
import datetime
import pickle
import os.path
import os
import shutil
from datetime import date
today = date.today()





PROVIDERS = {'indeed': Indeed, 'monster': Monster, 'glassdoor': GlassDoor}

providers_dict={
    0 : ['indeed', 'monster', 'glassdoor'],
    1: ['indeed', 'glassdoor']
}

get_prev_cache()

print('glob',glob_cache)
data  = pd.read_csv('/Users/riya/Desktop/data.csv')


df = pd.DataFrame(data)
df = df[['Company','Country']]

df.fillna('NA')

cur_date = str(datetime.datetime.now())

db = dd(dd)


for i in range(len(df)):
    key = df.iloc[i][0]
    coun = df.iloc[i][1]
    key = key.replace(' ','_')
    coun = coun.replace(' ','_')
    db[key][coun] = cur_date


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



for i in glob_cache.keys():
    for j in glob_cache[i].keys():
        print(i,j)




def lambda_handler(event,context):
    for i in range(len(keyword)):
        kword = keyword[i]
        ctry = countries[i]
        if(len(kword) < 5):
            continue
        kword = clean(kword)

        print('Keyword: ', kword)
        print('Country: ', ctry)
        file_name = 'search/{0}'.format(str(kword + '-' + ctry))
        # get current timestamp
       
        current_date = today.strftime("%d-%m-%Y")
        src_fpath = file_name
        dest_fpath = current_date + "/" + file_name
        #create folder if it doesn't exists
        if not os.path.exists(current_date):
            os.makedirs(current_date)

        if((kword not in glob_cache) and (ctry not in glob_cache[kword])):
            glob_cache[kword][ctry]=cur_date
        else:
            shutil.copy(src_fpath, dest_fpath)
            print('country already in hash')
            continue    #Have to take this file from local and push it to drive
        if(ctry in ctry_hash):
            curr = 0
        else:
            curr = 1
            print('Country not supported by monster!')
        try:
            temp_ctry = ctry.replace('_',' ')
            temp_kword = kword.replace('_',' ')
            config =    {
                            'output_path': 'search',
                            'providers': providers_dict[curr],
                            'search_terms': {
                                                'region': {
                                                                'city': temp_ctry, 
                                                                'country': temp_ctry,
                                                                'radius': 25
                                                        },
                                                'keywords': [temp_kword]
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
                            'master_list_path': 'search/{0}'.format(str(temp_kword + '-' + temp_ctry)),
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
                    #print('hi')
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
    file = open('global_hash.txt','w')
    for i in db.keys():
        for j in db[i].keys():
            file.write(str(i)+' ')
            file.write(str(j)+' ')
            file.write(str(db[i][j]) + ' ')
    
    file.close()

'''s3 = boto3.client('s3')
s3.upload_file(config['master_list_path'], S3_BUCKET_NAME, 'master_list.csv')
os.system("ls /tmp/")'''

    
lambda_handler(1,1)

