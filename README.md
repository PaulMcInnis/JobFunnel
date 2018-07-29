# JobPy:

Easily automated tool for scraping job postings to `.xlsx` using `python3`, `beautifulsoup4` and `pandas`

### How to use
1. Set your job search preferences in `config/search_terms.json` (or use `-kw`)
1. Execute `python3 run.py` to scrape all-available job listings from indeed
1. Review jobs in `jobs_masterlist.xslx`, set undesired jobs `state` to `filtered`, note that any custom states (i.e `applied`) are preserved in the spreadsheet

To update active filters and to see any `new` jobs going forwards, just run again, and review the spreadsheet, sorting by `new` state jobs with a filter-box

The resulting spreadsheet looks like this:

![masterlist.xslx](https://github.com/PaulMcInnis/JobPy/blob/master/demo.png "masterlist.xlsx")

### Notes
* indeed's http links are clickable in the excel output
* This system is easily automated to run nightly with crontab
* Check `jobpy.log` for output
