# Bateman's 4chan Scraper

This is a command line based program that saves attachments from threads on [4chan.org](https://www.4chan.org) whose OPs contain a keyword the user is interested in. Special requests and oneoffs can also be made. The unofficial 4chan archive site [4plebs.org](https://www.4plebs.org) is used to scrape threads not directly found on 4chan. The sites' APIs are used to achieve this.

## Files

The main script to run is `4chan Scraper.py`, written in Python 3.8. This will create a config file `scraperconfig.json` that stores keywords and data on threads of interest, to ensure they are remembered lest the threads are archived between scrapes.

Attachments are by default saved in the directory `downloaded`, though using the `-f` flag can change this.

`saosuite` is a directory containing auxiliary scripts.

## Commands
```
usage: 4chan Scraper.py

-h, --help
Show help

-l, --logo
Print SAO logo and program version

-u, --update
Update the lists of threads to scraped, but do not scrape them now. Also prunes threads of no further interest, ie those of keywords no longer being scraped for.

-s, --scrape
Calls --update and then scrapes

-p, --plebs
Force the use of 4plebs as the source of thread JSON and attachments for pleb boards. Affects flags --oneoff and --scrape

-v, --view
View the current requests, keywords, and blacklist

-f, --filename FILENAME
Specify the format of download filenames: default is 'downloaded/%(boardcode)s/%(opno)s %(keyword)s/%(no)s%(ext)s'. A full list of formatting parameters can be found in the section 'Filename Formatting Parameters'

-o, --oneoff ONEOFF
Perform a oneoff scrape of a specified thread of the form 'boardcode:opno:tag'. This ignores the config, whether the thread has been scraped before or not, or is blacklisted etc. 'tag' is optional, by default it is 'oneoff'

-r, --request REQUEST
Toggle the scraping of a specially requested thread in the form 'boardcode:opno:tag'. This overrides the blacklist. 'tag' is optional, by default it is 'request'

-a, --add ADD
Add keywords to scrape for in the form 'boardcode:word1,word2,...,wordn'

-d, --delete DELETE
Delete keywords to no longer search for in the form 'boardcode:word1,word2,...,wordn'

-b, --blacklist BLACKLIST
Toggle the blacklisting of a thread to not be scraped in the form 'boardcode:opno'
```

## Filename Formatting Parameters

- `%(boardcode)s`
- `%(opno)s`
- `%(keyword)s`
- `%(no)s` - The post number
- `%(tim)s` - The time the attachment was uploaded
- `%(ext)s` - The attachment extension
- `%(md5Hex)s` - MD5 hash hex of the file
- `%(originalFilename)s` - The filename as it was uploaded to 4chan with
- `%(posterName)s` - The uploader poster's name, usually 'Anonymous'
- `%(modus)s` - '4chan' or '4plebs' depending on where the attachment was downloaded from
