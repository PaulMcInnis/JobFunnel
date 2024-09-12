# Crontab

This document is a guide to setting up JobFunnel with Crontab.

### Installing Crontab

Use `apt-get` to install on Debian.

```bash
sudo apt-get install cron
```

### Setting up Jobs

To get JobFunnel working in crontab find a location where you want to store
jobs. <br /> Somewhere like:

```
~/Documents/jobfunnel
```

Copy the shell script `cronjob.sh` from this directory to
`~/Documents/jobfunnel`. <br /> Make the shell script executable by running
`chmod +x ~/Documents/jobfunnel/cronjob.sh`.

Make a folder for each geographical location you want to scrape:

```
username:~/Documents/jobfunnel$ ls -l
total 24
drwxr-xr-x 3 username username 4096 Sep 20 12:49 burlington
drwxr-xr-x 3 username username 4096 Sep 20 02:42 calgary
-rwxr-xr-x 1 username username  323 Sep 20 13:46 cronjob.sh
drwxr-xr-x 3 username username 4096 Sep 20 10:55 edmonton
drwxr-xr-x 3 username username 4096 Sep 20 11:04 hamilton
drwxr-xr-x 3 username username 4096 Sep 20 03:02 waterloo
```

Make a `settings.yaml` file for each folder representing a geographical region:

```
total 4
-rw-r--r-- 1 username username 689 Sep 20 11:05 settings.yaml
```

Do a test run by executing:

```bash
./cronjob.sh
```

## Setting up Crontab

To set up crontab for a specific user run:

```bash
crontab -u username -e
```

To run once each day, append to the bottom:

```
* 0 * * * cd ~/Documents/jobfunnel && ./cronjob.sh > cronjob.log 2>&1
```
