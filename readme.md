---
<img src="https://travis-ci.com/bunsenmurder/JobFunnel.svg?branch=dev" alt="Build Status" />
### About

As me and many others have found out, the process of job searching is very time consuming and riddled with annoyances; especially with online job boards where problems like reposts and filled jobs being posted jobs are way too common. Looking for a way to help automate this process, I found jobFunnel and decided to add some personal touches and fixes I think are essential for improving the tool and helping make the job search a little less garbaggio.

### Whats been done in this fork:

* Implementing a delaying algorithm so that you can respectively scrape job postings. 
* Upgrading the multi-threading module from [threading][thread] to  [concurrent.futures][conc_fut].
* Option to save filtered duplicates to a seperate file for enhancing filtering capabilities.
* Improving the detection accuracy of duplicate filter, and allowing for the ability to detect duplicate jobs within a single scrape dictionary.
* Implementing a jobID filter that checks the master list and duplicate list for filtered ids, to avoid re-scraping filtered jobs.
* Regex optimization wizardry :shipit:
* Improving saved data content retrieved for doing data science stuff.
* Optimizing a lot of the code to be more computationally efficient e.g. replacing for-loops with list comprehensions, or reducing usage of unnecessary repetition. 
* Date string parsing captures almost all fringe cases and is output to a more standard format (YYYY-MM-DD). 
* Add function ensure radius compatability between using diffrent domains(.com, .ca) and diffrent providers.
* Other misc. things to improve user experiance. 

### Usage Notes Part 2:
* **Saving Duplicates** <br/> 
Duplicates can be saved by turn the option in your ``settings.yaml` file or by using the `--save_dup` flag in the command line. The duplicates file would be stored in the same directory as your master list file under the name `duplicates_list.csv`
* **Setting Delay** <br/>
  Delay can be configured using a ``settings.yaml` file or using command line arguments.
  - `-d` lets you set your max delay value: ``funnel -s demo/settings.yaml -kw AI -d 15`
  - `-r` lets you specify if you want to use random delaying, and uses `-d` to control the range of randoms we pull from.
  - `-c` lets you specify if you want to use converging random delay, which is a diffrent mode of random delay where the possible random value is constrained to a smaller range over time till it becomes equal to your set delay. You need to set `-r` flag for this flag to work. Proper usage would look something like: `funnel -s demo/settings.yaml -kw AI -rcd 15`
  - `-md` lets you set a minimum delay value: `funnel -s demo/settings.yaml -d 15 -md 5` 
  - `--fun` controls what function is used to calculate delay, where you have the choice of selecting either ``constant`,  `linear`, or `sigmoid` delay: `funnel -s demo/settings.yaml -rcd 15 -md 5 --fun sigmoid` 

  To better understand how to configure delaying, check out [this Jupyter Notebook][delay_jp] I made breaking down how the delaying algorithm works with code and visualizations of how the arguments affect delaying behavior.

Since this is just a fork I will leave the original description at the bottom, which gives valuable instructions and provides credit to the original creators. Also for anyone interestested in Data Science stuff, check out [this other Jupyter Notebook][tfidf_jp] where I did some very rough exploratory analysis and experimentation with building the current implementation of the duplicate filter which uses TF-IDF and Cosine Similarity to achieve our duplicate filtering.

__*Note*__: If the scraper seems slow, that is on purpose. Delaying is enabled by default and can be turned off, but I HIGHLY recommend not doing that. You can try tweaking the delay settings if it seems too slow. 

---

<img src="images/jobfunnel_banner.png" alt="JobFunnel Banner" /> <br /> <br />

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
  

<!-- links -->

[masterlist]:demo/assests/demo.png "masterlist.csv"
[python]:https://www.python.org/
[demo]:demo/readme.md
[cron]:https://en.wikipedia.org/wiki/Cron
[cron_doc]:docs/crontab/readme.md
[conc_fut]:https://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
[thread]: https://docs.python.org/3.8/library/threading.html
[delay_jp]:https://github.com/bunsenmurder/Notebooks/blob/master/jobFunnel/delay_algorithm.ipynb
[tfidf_jp]:https://github.com/bunsenmurder/Notebooks/blob/master/jobFunnel/tf_idf%20analysis.ipynb