# JobFunnel

Automated tool for scraping job postings into a `.csv` file.

### Benefits over job search sites:

* Never see the same job twice!
* Browse all search results at once, in an easy to read/sort spreadsheet.
* Keep track of all explicitly new job postings in your area.
* See jobs from multiple job search sites all in one place.

The spreadsheet for managing your job search:

![masterlist.csv][masterlist]

### Installing JobFunnel

```
pip install git+https://github.com/PaulMcInnis/JobFunnel.git
funnel --help
```

If you want to develop JobFunnel, you may want to install it in-place:

```
git clone git@github.com:PaulMcInnis/JobFunnel.git jobfunnel
pip install -e ./jobfunnel
funnel --help
```

### Using JobFunnel

1. Set your job search preferences in the `yaml` configuration file (or use `-kw`).
1. Run `funnel` to scrape all-available job listings.
1. Review jobs in the master list, set any undesired jobs `status` to `archive`, these jobs will be removed from the `.csv` next time you run `funnel`.
1. If you get an `interview`/`offer` or are `rejected`, update the job `status`.

__*Note*__: `rejected` jobs will be filtered out and will disappear from the output `.csv`.

### Usage Notes

* Note that any custom states (i.e `applied`) are preserved in the spreadsheet.
* To update active filters and to see any `new` jobs going forwards, just run `funnel` again, and review the `.csv` file.
* You can keep multiple search results across multiple `.csv` files:
```
funnel -kw Python -o python_search
funnel -kw AI Machine Learning -o ML_search
```
* Filter undesired companies by providing your own `yaml` configuration and adding them to the black list (see `JobFunnel/jobfunnel/config/settings.yaml`).
* JobFunnel can be easily automated to run nightly with [crontab][cron]
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

for dir in */ ; do
    funnel -s $dir/settings.yaml
done
```
where each `settings.yaml` file can point to it's own directory.

<!-- links -->

[masterlist]:https://github.com/PaulMcInnis/JobFunnel/blob/master/demo.png "masterlist.csv"
[cron]:https://en.wikipedia.org/wiki/Cron
