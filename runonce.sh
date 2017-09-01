#!/bin/bash

python3 masterlist_tofilterjson.py # add any existing changes in masterlist.xlsx, if present
python3 indeed_topickle.py # get current listings
python3 pickle_tomasterlist.py # add current listings to masterlist.xlsx
