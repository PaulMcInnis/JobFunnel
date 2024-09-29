<img src="logo/jobfunnel_banner.svg" alt="JobFunnel Banner" width=400/><br/>
[![Code Coverage](https://codecov.io/gh/PaulMcInnis/JobFunnel/branch/master/graph/badge.svg)](https://codecov.io/gh/PaulMcInnis/JobFunnel)

Automated tool for scraping job postings into a `.csv` file.

### Benefits over job search sites:

* Never see the same job twice!
* No advertising.
* See jobs from multiple job search websites all in one place.

![masterlist.csv][masterlist]


# Installation

_JobFunnel requires [Python][python] 3.11 or later._

```
pip install git+https://github.com/PaulMcInnis/JobFunnel.git
```

# Usage
By performing regular scraping and reviewing, you can cut through the noise of even the busiest job markets.

## Configure
You can search for jobs with YAML configuration files or by passing command arguments.

Download the demo [settings.yaml][demo_yaml] by running the below command:

```
wget https://git.io/JUWeP -O my_settings.yaml
```

_NOTE:_
* _It is recommended to provide as few search keywords as possible (i.e. `Python`, `AI`)._

* _JobFunnel currently supports `CANADA_ENGLISH`, `USA_ENGLISH`, `UK_ENGLISH`, `FRANCE_FRENCH`, and `GERMANY_GERMAN` locales._

## Scrape

Run `funnel` with your settings YAML to populate your master CSV file with jobs from available providers:

```
funnel load -s my_settings.yaml
```

## Review

Open the master CSV file and update the per-job `status`:

* Set to `interested`, `applied`, `interview` or `offer` to reflect your progression on the job.

* Set to `archive`, `rejected` or `delete` to remove a job from this search. You can review 'blocked' jobs within your `block_list_file`.

# Advanced Usage

* **Automating Searches** <br />
  JobFunnel can be easily automated to run nightly with [crontab][cron] <br />
  For more information see the [crontab document][cron_doc].

* **Writing your own Scrapers** <br />
  If you have a job website you'd like to write a scraper for, you are welcome to implement it, Review the [Base Scraper][basescraper] for implementation details.

* **Remote Work** <br />
  Bypass a frustrating user experience looking for remote work by setting the search parameter `remoteness` to match your desired level, i.e. `FULLY_REMOTE`.

* **Adding Support for X Language / Job Website** <br />
  JobFunnel supports scraping jobs from the same job website across locales & domains. If you are interested in adding support, you may only need to define session headers and domain strings, Review the [Base Scraper][basescraper] for further implementation details.

* **Blocking Companies** <br />
  Filter undesired companies by adding them to your `company_block_list` in your YAML or pass them by command line as `-cbl`.

* **Job Age Filter** <br />
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
  funnel --recover
  ```

* **Running by CLI** <br />
  You can run JobFunnel using CLI only, review the command structure via:
  ```
  funnel inline -h
  ```
 
# CAPTCHA
  JobFunnel does not solve CAPTCHA. If, while scraping, you receive a 
  `Unable to extract jobs from initial search result page:\` error. 
  Then open that url on your browser and solve the CAPTCHA manually.

# Developer Guide

For contributors and developers who want to work on JobFunnel, this section will guide you through setting up the development environment and the tools we use to maintain code quality and consistency.

## Developer Mode Installation

To get started, install JobFunnel in **developer mode**. This will install all necessary dependencies, including development tools such as testing, linting, and formatting utilities.

To install JobFunnel in developer mode, use the following command:

```bash
pip install -e '.[dev]'
```

This command not only installs the package in an editable state but also sets up pre-commit hooks for automatic code quality checks.

## Pre-Commit Hooks

The following pre-commit hooks are configured to run automatically when you commit changes to ensure the code follows consistent style and quality guidelines:

- `Black`: Automatically formats Python code to ensure consistency.
- `isort`: Sorts and organizes imports according to the Black style.
- `Prettier`: Formats non-Python files such as YAML and JSON.
- `Flake8`: Checks Python code for style guide violations.

While the pre-commit package is installed when you run `pip install -e '.[dev]'`, you still need to initialize the hooks by running the following command once:

```bash
pre-commit install
```

### How Pre-Commit Hooks Work

The pre-commit hooks will automatically run when you attempt to make a commit. If any formatting issues are found, the hooks will fix them (for Black and isort), or warn you about style violations (for Flake8). This ensures that all committed code meets the project’s quality standards.

You can also manually run the pre-commit hooks at any time with:

```bash
pre-commit run --all-files
```

This is useful to check the entire codebase before committing or as part of a larger code review. Please fix all style guide violations (or provide a reason to ignore) before committing to the repository.

## Running Tests

We use `pytest` to run tests and ensure that the code behaves as expected. Code coverage is automatically generated every time you run the tests.

To run all tests, use the following command:

```bash
pytest
```

This will execute the test suite and automatically generate a code coverage report.

If you want to see a detailed code coverage report, you can run:

```bash
pytest --cov-report=term-missing
```

This will display which lines of code were missed in the test coverage directly in your terminal output.



<!-- links -->
[requirements]:requirements.txt
[masterlist]:demo/demo.png "masterlist.csv"
[demo_yaml]:demo/settings.yaml
[python]:https://www.python.org/
[basescraper]:jobfunnel/backend/scrapers/base.py
[cron]:https://en.wikipedia.org/wiki/Cron
[cron_doc]:docs/crontab/readme.md
[conc_fut]:https://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
[thread]: https://docs.python.org/3.11/library/threading.html
[delay_jp]:https://github.com/bunsenmurder/Notebooks/blob/master/jobFunnel/delay_algorithm.ipynb
