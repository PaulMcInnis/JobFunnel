# JobPy:

Easily automated tool for scraping job postings to `.csv` using `python3` and `beautifulsoup4`

### Benefits over job search sites
* never see the same job twice!
* browse all search results at once, in an easy to read/sort spreadsheet
* keep track of all explicitly new job postings in your area
* see jobs from multiple job search sites all in one place

The spreadsheet for managing your job search:

![masterlist.csv](https://github.com/PaulMcInnis/JobPy/blob/master/demo.png "masterlist.csv")

### How to use
1. Install requirements: `pip3 install -r requirements.txt`
1. Set your job search preferences in `config/search_terms.json` (or use `-kw`)
1. Execute `python3 run.py` to scrape all-available job listings from indeed
1. Review jobs in `jobs_masterlist.csv`, set any undesired jobs `status` to `archive`, these jobs will be removed from .csv next time you run `run.py`
1. If you get an `interview`/`offer` or are `rejected`, update the job `status`, note that `rejected` jobs will be filtered out and will disappear from the output .csv

### Usage Notes
* note that any custom states (i.e `applied`) are preserved in the spreadsheet
* to update active filters and to see any `new` jobs going forwards, just `python3 run.py` again, and review .csv
* you can keep multiple search results across multiple .csv files: i.e: `python3 run.py -kw Python -o data/python_masterlist.csv` for python jobs, and `python3 run.py -kw AI Machine Learning -o data/ML_masterlist.csv` for ML jobs
* by adding job undesired i.e. consulting companies to the `config/blacklist.json`, you can exclude them from results
* system is easily automated to run nightly with crontab
