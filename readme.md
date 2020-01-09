<img src="images/jobfunnel_banner.png" alt="JobFunnel Banner" /> <br /> <br />
<img src="https://travis-ci.com/PaulMcInnis/JobFunnel.svg?branch=master" alt="Build Status" >

Automated tool for scraping job postings into a `.csv` file.

### Benefits over job search sites:

* Never see the same job twice!
* Browse all search results at once, in an easy to read/sort spreadsheet.
* Keep track of all explicitly new job postings in your area.
* See jobs from multiple job search sites all in one place.

The spreadsheet for managing your job search:

![masterlist.csv][masterlist]

### Dependencies

JobFunnel requires [Python][python] 3.6 or later. <br />
All dependencies are listed in `setup.py`, and can be installed automatically with `pip` when installing JobFunnel.

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
1. Review jobs in the master-list, update the job `status` to other values such as `interview` or `offer`.
1. Set any undesired job `status` to `archive`, these jobs will be removed from the `.csv` next time you run `funnel`.
1. Check out [demo/readme.md][demo] if you want to try the demo.

__*Note*__: `rejected` jobs will be filtered out and will disappear from the output `.csv`.

### Usage Notes

* **Custom Status** <br/>
  Note that any custom states (i.e `applied`) are preserved in the spreadsheet.

* **Running Filters** <br />
  To update active filters and to see any `new` jobs going forwards, just run `funnel` again, and review the `.csv` file.

* **Recovering Lost Master-list** <br />
  If ever your master-list gets deleted you still have the historic pickle files. <br />
  Simply run `funnel --recover` to generate a new master-list.

* **Managing Multiple Searches** <br />
  You can keep multiple search results across multiple `.csv` files:
  ```
  funnel -kw Python -o python_search
  funnel -kw AI Machine Learning -o ML_search
  ```

* **Filtering Undesired Companies** <br />
  Filter undesired companies by providing your own `yaml` configuration and adding them to the black list (see `JobFunnel/jobfunnel/config/settings.yaml`).

* **Automating Searches** <br />
  JobFunnel can be easily automated to run nightly with [crontab][cron] <br />
  For more information see the [crontab document][cron_doc].

* **Reviewing Jobs in Terminal** <br />
  You can review the job list in the command line:
  ```
  column -s, -t < master_list.csv | less -#2 -N -S
  ```
* **Saving Duplicates** <br /> 
  You can save removed duplicates in a separate file, which is stored in the same place as your master list: <br />
  ```
  funnel --save_dup
  ```
* **Respectful Delaying** <br />
  Respectfully scrape your job posts with our built-in delaying algorithm, which can be configured using a config file (see `JobFunnel/jobfunnel/config/settings.yaml`) or with command line arguments:
  - `-d` lets you set your max delay value: `funnel -s demo/settings.yaml -kw AI -d 15`
  - `-r` lets you specify if you want to use random delaying, and uses `-d` to control the range of randoms we pull from: <br /> `funnel -s demo/settings.yaml -kw AI -r`
  - `-c` specifies converging random delay, which is an alternative mode of random delay. Random delay needed to be turned on as well for it to work. Proper usage would look something like this: <br /> `funnel -s demo/settings.yaml -kw AI -r -c` 
  - `-md` lets you set a minimum delay value: <br /> `funnel -s demo/settings.yaml -d 15 -md 5`
  - `--fun` can be used to set which mathematical function (`constant`,  `linear`, or `sigmoid`) is used to calculate delay: <br /> `funnel -s demo/settings.yaml --fun sigmoid` 
  - `--no_delay` Turns off delaying, but it's usage is not recommended.

  To better understand how to configure delaying, check out [this Jupyter Notebook][delay_jp] breaking down the algorithm step by step with code and visualizations.

<!-- links -->
[masterlist]:demo/assests/demo.png "masterlist.csv"
[python]:https://www.python.org/
[demo]:demo/readme.md
[cron]:https://en.wikipedia.org/wiki/Cron
[cron_doc]:docs/crontab/readme.md
[conc_fut]:https://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
[thread]: https://docs.python.org/3.8/library/threading.html
[delay_jp]:https://github.com/bunsenmurder/Notebooks/blob/master/jobFunnel/delay_algorithm.ipynb
