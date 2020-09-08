<img src="images/jobfunnel_banner.png" alt="JobFunnel Banner" /> <br /> <br />
[![Build Status](https://travis-ci.com/PaulMcInnis/JobFunnel.svg?branch=master)](https://travis-ci.com/PaulMcInnis/JobFunnel)
[![Code Coverage](https://codecov.io/gh/PaulMcInnis/JobFunnel/branch/master/graph/badge.svg)](https://codecov.io/gh/PaulMcInnis/JobFunnel)

Automated tool for scraping job postings into a `.csv` file.

----
__*Note (Sept 5 2020)*__: If you are having trouble scraping jobs on current release, please try `ABCJobFunnel` branch and report any bugs you encounter! Current known issues discussion in thread here: [#90](https://github.com/PaulMcInnis/JobFunnel/pull/90)

Install this branch via:
```
git clone git@github.com:PaulMcInnis/JobFunnel.git jobfunnelabc
cd jobfunnelabc
git checkout ABCJobFunnel
cd ../
pip install -e jobfunnelabc
```
----

### Benefits over job search sites:

* Never see the same job twice!
* Browse all search results at once, in an easy to read/sort spreadsheet.
* Keep track of all explicitly new job postings in your area.
* See jobs from multiple job search websites all in one place.
* Compare job search results across locations

The spreadsheet for managing your job search:

![masterlist.csv][masterlist]

----

### Installation

_JobFunnel requires [Python][python] 3.6 or later._

All dependencies are listed in `setup.py`, and can be installed automatically with `pip`.

```
pip install git+https://github.com/PaulMcInnis/JobFunnel.git
```

If you want to develop JobFunnel, you can install it in-place:

```
git clone git@github.com:PaulMcInnis/JobFunnel.git
pip install -e ./JobFunnel
```

----

### Using JobFunnel

After installation you can search for jobs with YAML configuration files or by passing command arguments.

Run the below commands to perform a demonstration job search that saves results in your local directory within a folder called `demo_job_search_results`.

```
wget https://www.github.com/PaulMcInnis/JobFunnel/demo/settings.yaml
funnel load -s settings.yaml
```

If you would prefer to use the extensive CLI arguments in-place of a configuration
YAML file, review the command structure by running the below command:

```
funnel custom -h
```

The recommended approach is to build your own `settings.yaml` file from the example provided in [demo/readme.md][demo] and run `funnel load -s <your_settings.yaml>`

----

### Reviewing Results

Follow these steps to continuously-improve your job search results CSV:

1. Set your job search preferences in a `yaml` configuration file.
2. Run `funnel load -s ...` to scrape all-available job listings.
3. Review jobs in the master-list CSV, and update the job `status` to reflect your interest or progression: `interested`, `applied`, `interview` or `offer`.
4. Set any a job `status` to `archive`, `rejected` or `delete` to  remove them from the `.csv`. ___Note: listings you filter away by `status` are persistant___

----

### Job Statuses

_NOTE: `status` values are not case-sensitive_

| Status | Purpose |
| ------ | ------------- |
| `NEW`  | The job has been freshly scraped, likely un-reviewed. |
| `ARCHIVE`, `REJECTED`, `DELETE`, `OLD` | The job will be added to filter lists and will not appear in CSV again. You can see any jobs which have been added to your filter lists by reviewing your `block_list_file` JSON. |
| `INTERESTED`, `APPLY`, `APPLIED`, `ACCEPTED`, `INTERVIEWED`, `INTERVIEWING` | Use these to boost visibility of desirable jobs or to track progress. |

----

### Advanced Usage

* **Managing Multiple Searches** <br />
  JobFunnel works best if you keep distinct searches in their own `.csv` files, i.e.:
  ```
  funnel custom -kw Python -c Waterloo -ps ON -l CANADA_ENGLISH -o canada_python
  funnel custom -kw AI Machine Learning -c Seattle -ps WA -l USA_ENGLISH -o USA_ML
  ```

* **Automating Searches** <br />
  JobFunnel can be easily automated to run nightly with [crontab][cron] <br />
  For more information see the [crontab document][cron_doc].

* **Writing your own Scrapers** <br />
  If you have a job website you'd like to write a scraper for, you are welcome to implement it, Review the [BaseScraper][BaseScraper] for implementation details.

* **Adding Support for X Language Job Website** <br />
  JobFunnel supports scraping jobs from the same job website across differnt locales. If you are interested in adding support, you may only need to define session headers and domain strings, Review the [BaseScraper][BaseScraper] for further implementation details.

* **Recovering Lost Master-list** <br />
  JobFunnel can re-build your master CSV from your search's scrape cache, where all the historic scrape data is located:
  ```
  funnel --recover load -s my_search_settings.yaml
  ```

* **Filtering Undesired Companies** <br />
  Filter undesired companies by adding them to your `company_block_list` in your YAML or pass them by command line as `-cbl`.

* **Filtering Old Jobs**<br />
  You can configure the maximum age of scraped listings (in days) by setting `max_listing_days` in your YAML, or by passing:
  ```
  funnel -max-listing-days 30
  ```

* **Reviewing Jobs in Terminal** <br />
  You can review the job list in the command line:
  ```
  column -s, -t < master_list.csv | less -#2 -N -S
  ```

* **Saving Duplicates** <br />
  It is recommended that you save duplicate jobs detected via content match to ensure detections persist. You can configure this path via `duplicates_list_file` in YAML or by passing command line:
  ```
  funnel -dl my_duplicates_list.json
  ```

* **Respectful Delaying** <br />
  Respectfully scrape your job posts with our built-in delaying algorithm, which can be configured using a config file (see `JobFunnel/jobfunnel/config/settings.yaml`) or with command line arguments:
  - `-delay-max` lets you set your max delay value in seconds.
  - `-delay-min` lets you set a minimum delay value in seconds. <br /> _NOTE: must be smaller than maximum_
  - `--delay-random` lets you specify if you want to use random delaying, and uses `-delay-max` to control the range of randoms we pull from.
  - `--delay-converging` specifies converging random delay, which is an alternative mode of random delay. <br />_NOTE: this is intended to be used in combination with `--delay-random`_
  - `-delay-algorithm` can be used to set which mathematical function (`constant`,  `linear`, or `sigmoid`) is used to calculate delay.

  To better understand how to configure delaying, check out [this Jupyter Notebook][delay_jp] which breaks down the algorithm step by step with code and visualizations.

<!-- links -->
[masterlist]:demo/assests/demo.png "masterlist.csv"
[python]:https://www.python.org/
[demo]:demo/readme.md
[basescraper]:jobfunnel/backend/scraper/base.py
[cron]:https://en.wikipedia.org/wiki/Cron
[cron_doc]:docs/crontab/readme.md
[conc_fut]:https://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
[thread]: https://docs.python.org/3.8/library/threading.html
[delay_jp]:https://github.com/bunsenmurder/Notebooks/blob/master/jobFunnel/delay_algorithm.ipynb
