<img src="logo/jobfunnel_banner.svg" alt="JobFunnel Banner" width=400/><br/>
[![Build Status](https://travis-ci.com/PaulMcInnis/JobFunnel.svg?branch=master)](https://travis-ci.com/PaulMcInnis/JobFunnel)
[![Code Coverage](https://codecov.io/gh/PaulMcInnis/JobFunnel/branch/master/graph/badge.svg)](https://codecov.io/gh/PaulMcInnis/JobFunnel)

Automated tool for scraping job postings into a `.csv` file.

### Benefits over job search sites:

* Never see the same job twice!
* No advertising.
* See jobs from multiple job search websites all in one place.
* Compare job search results between locations, and queries.

![masterlist.csv][masterlist]


# Installation

_JobFunnel requires [Python][python] 3.8 or later._

```
pip install git+https://github.com/PaulMcInnis/JobFunnel.git
```

# Usage

After installation you can search for jobs with YAML configuration files or by passing command arguments.

## Configuring

Begin by customizing our [demo settings][demo_yaml] to suit your needs:
```
wget https://raw.githubusercontent.com/PaulMcInnis/JobFunnel/master/demo/settings.yaml -O my_settings.yaml
nano my_settings.yaml
```

_NOTE: It is recommended to provide as few search keywords as possible (i.e. try using `AI`, `Python` instead of `Software`, `Developer`, `Python`, `AI`)._

## Scraping
Run `funnel` to populate your master CSV file with jobs:

```
funnel load -s my_settings.yaml
```

## Reviewing

Open the master CSV file and update the jobs' `status`:

* Set to `interested`, `applied`, `interview` or `offer` to reflect interest or progression on the job.

* Set to `archive`, `rejected` or `delete` to  remove a job from the `.csv` permanently (for this search). You can review 'blocked' jobs within your `block_list_file`.

By combining regular scraping with regular reviewing, you can cut through the noise of even the busiest job markets.

# Advanced Usage

* **Automating Searches** <br />
  JobFunnel can be easily automated to run nightly with [crontab][cron] <br />
  For more information see the [crontab document][cron_doc].

* **Writing your own Scrapers** <br />
  If you have a job website you'd like to write a scraper for, you are welcome to implement it, Review the [Base Scraper][basescraper] for implementation details.

* **Adding Support for X Language / Job Website** <br />
  JobFunnel supports scraping jobs from the same job website across locales & domains. If you are interested in adding support, you may only need to define session headers and domain strings, Review the [Base Scraper][basescraper] for further implementation details.

* **Blocking Companies** <br />
  Filter undesired companies by adding them to your `company_block_list` in your YAML or pass them by command line as `-cbl`.

* **Job Age Filter**<br />
  You can configure the maximum age of scraped listings (in days) by configuring `max_listing_days`.

* **Reviewing Jobs in Terminal** <br />
  You can review the job list in the command line:
  ```
  column -s, -t < master_list.csv | less -#2 -N -S
  ```

* **Respectful Delaying** <br />
  Respectfully scrape your job posts with our built-in delaying algorithms.

  To better understand how to configure delaying, check out [this Jupyter Notebook][delay_jp] which breaks down the algorithm step by step with code and visualizations.

* **Recovering Lost Data** <br />
  JobFunnel can re-build your master CSV from your `cache_folder` where all the historic scrape data is located:
  ```
  funnel --recover ...
  ```

* **Running by CLI** <br />
  You can run JobFunnel using CLI only, review the command structure via:
  ```
  funnel custom -h
  ```

<!-- links -->
[requirements]:requirements.txt
[masterlist]:demo/demo.png "masterlist.csv"
[demo_yaml]:demo/settings.yaml
[python]:https://www.python.org/
[basescraper]:jobfunnel/backend/scrapers/base.py
[cron]:https://en.wikipedia.org/wiki/Cron
[cron_doc]:docs/crontab/readme.md
[conc_fut]:https://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
[thread]: https://docs.python.org/3.8/library/threading.html
[delay_jp]:https://github.com/bunsenmurder/Notebooks/blob/master/jobFunnel/delay_algorithm.ipynb
