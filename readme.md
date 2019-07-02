# JobPy

Automated tool for scraping job postings into a `.csv` file.

### Benefits over job search sites:

* Never see the same job twice!
* Browse all search results at once, in an easy to read/sort spreadsheet.
* Keep track of all explicitly new job postings in your area.
* See jobs from multiple job search sites all in one place.

The spreadsheet for managing your job search:

![masterlist.csv][masterlist]

### Installing JobPy

```
pip install git+https://github.com/PaulMcInnis/JobPy.git
jobpy --help
```

### Using JobPy

1. Set your job search preferences in the `yaml` configuration file (or use `-kw`).
1. Run `jobpy` to scrape all-available job listings.
1. Review jobs in the master list, set any undesired jobs `status` to `archive`, these jobs will be removed from the `.csv` next time you run `jobpy`.
1. If you get an `interview`/`offer` or are `rejected`, update the job `status`.

__*Note*__: `rejected` jobs will be filtered out and will disappear from the output `.csv`.

### Usage Notes

* Note that any custom states (i.e `applied`) are preserved in the spreadsheet.
* To update active filters and to see any `new` jobs going forwards, just run `jobpy` again, and review the `.csv` file.
* You can keep multiple search results across multiple `.csv` files:
```
jobpy -kw Python -o python_search
jobpy -kw AI Machine Learning -o ML_search
```
* Filter undesired companies by providing your own `yaml` configuration and adding them to the black list (see `JobPy/jobpy/config/settings.yaml`).
* JobPy can be easily automated to run nightly with [crontab][cron]
* You can review the job list in the command line:
```
column -s, -t < master_list.csv | less -#2 -N -S
```
* You can run several independent job searches with a directory structure like the following:

```bash
python_search/
  |_ settings.yaml
ML_search/
  |_ settings.yaml

for d in */ ; do
    jobpy -s $d/settings.yaml
done
```
where each `settings.yaml` file can point to it's own directory.

<!-- links -->

[masterlist]:https://github.com/PaulMcInnis/JobPy/blob/master/demo.png "masterlist.csv"
[cron]:https://en.wikipedia.org/wiki/Cron
