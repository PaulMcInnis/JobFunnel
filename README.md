# JobPy:

Easily automated tool for scraping job postings to ```.xlsx``` using ```python3```, ```beautifulsoup4``` and ```pandas```

### How to use
1. execute ```runonce.sh```
2. review jobs in ```jobs_masterlist.xslx```, set undesired jobs ```state``` to ```filtered```, note that any custom states such as ```applied``` are preserved in the spreadsheet
3. run ```pickle_tomasterlist.py``` (or ```runonce.sh```) to add any jobs of ```filtered``` state to the ```filterlist.json``` and to remove them from ```jobs_masterlist.xlsx```

The ```jobs_masterlist.xslx``` is what should be reviewed by the user, setting jobs to appropriate states, for example ```applied```. To update active filters and to see any ```new``` jobs going forwards, just run ```runonce.sh```, and review the spreadsheet, sorting by ```new``` state jobs.

The resulting spreadsheet looks like this:
![alt text](https://github.com/PaulMcInnis/JobPy/demo.png "JobPy's masterlist.xlsx")

### Notes
* links are clickable in the excel output
* This system is easily automated to run nightly with crontab by running included bash script ```runonce.sh```
* Check jobpy.log for output


