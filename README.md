# JobPy:

Easily automated tool for scraping job postings to `.csv` using `python3` and `beautifulsoup4`

### How to use
1. install requirements: `pip3 install -r requirements.txt`
1. Set your job search preferences in `config/search_terms.json` (or use `-kw`)
1. Execute `python3 run.py` to scrape all-available job listings from indeed
1. Review jobs in `jobs_masterlist.csv`, set any undesired jobs `status` to `archive`, note that any custom states (i.e `applied`) are preserved in the spreadsheet

To update active filters and to see any `new` jobs going forwards, just run again, and review the spreadsheet, sorting by `new` state jobs with a filter-box

The resulting spreadsheet looks like this:

![masterlist.csv](https://github.com/PaulMcInnis/JobPy/blob/master/demo.png "masterlist.csv")

### Benefits over indeed.ca
* never see the same job twice!
* browse all search results at once, in an easy to read/sort spreadsheet
* system is easily automated to run nightly with crontab
* keep track of jobs you have applied to, even if they are not on indeed.ca, by adding them to the .csv
* keep track of new job postings in your area
