# Bateman's 4chan Scraper

This is a command line based program that saves attachments from threads on [4chan.org](https://www.4chan.org) whose OPs contain a keyword the user is interested in. Special requests and oneoffs can also be made. The unofficial 4chan archive site [4plebs.org](https://www.4plebs.org) is used to scrape threads not directly found on 4chan. The sites' APIs are used to achieve this.

## Files

The main script to run is `4chan Scraper.py`, written in Python 3.8. This will create a config file `scraperconfig.json` that stores keywords and data on threads of interest, to ensure they are remembered lest the threads are archived between scrapes.

Attachments are saved in the directory `downloaded`.

`saosuite` is a directory containing auxiliary scripts.

## Commands
```
usage: 4chan Scraper.py

[--help]
Show help

[--logo]
Print SAO logo when run

[--update]
Update the lists of threads to scraped, but do not scrape them now. Also prunes threads of no further interest, ie those of keywords no longer being scraped for.

[--scrape]
Calls --update and then scrapes

[--plebs]
Only use 4plebs as source of thread JSON and attachments. Affects flags --oneoff and --scrape

[--view]
View the current requests, keywords, and blacklist

[--oneoff ONEOFF]
Perform a oneoff scrape of a specified thread of the form 'boardcode:opno:tag'. This ignores the config, whether the thread has been scraped before or not, or is blacklisted etc. 'tag' is optional, by default it is 'oneoff'

[--request REQUEST]
Toggle the scraping of a specially requested thread in the form 'boardcode:opno:tag'. This overrides the blacklist. 'tag' is optional, by default it is 'request'

[--add ADD]
Add keywords to scrape for in the form 'boardcode:word1,word2,...,wordn'

[--delete DELETE]
Delete keywords to no longer search for in the form 'boardcode:word1,word2,...,wordn'

[--blacklist BLACKLIST]
Toggle the blacklisting of a thread to not be scraped in the form 'boardcode:opno'
```
