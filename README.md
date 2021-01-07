# Bateman's 4chan Scraper

This is a command line based program that saves attachments from threads on [4chan.org](https://www.4chan.org) whose OPs contain a keyword the user is interested in. Special thread requests can also be made. The unofficial 4chan archive site [4plebs.org](https://www.4plebs.org) is used to scrape threads not directly found on 4chan. The sites' APIs are used to achieve this.

## Files

The main program to run is `4chan Scraper.py`, written in Python 3.8. When run the program will create a config file `scraperconfig.json` in the current directory, and attachments scraped will be saved in the folder `downloaded` alongside the program.

## Commands
```
usage: 4chan Scraper.py
[-h]
[--logo]
[--update]
[--scrape]
[--plebs]
[--view]
[--request REQUEST]
[--add ADD]
[--delete DELETE]
[--blacklist BLACKLIST]
```

Running `python '4chan Scraper.py' -h` will display the help page that details the commands

## Features

- Scrape thread attachments with minimal effort
- Progress bar to show scraping progress
- Add and remove boards with their own set of keywords to scrape for
- Make special requests to scrape custom threads
- Request to scrape all archived threads of interest from 4plebs
- Blacklist threads to not scrape
- View what keywords are being scraped for, special requests are being made, and blacklisted threads
- Option to auto-quit once the current scraping session has finished
- Inbuilt `-h` help command
- **Automatic:** If a thread or file is not found on 4chan, and the board is being archived on 4plebs, it is then searched for on 4plebs
- **Automatic:** Threads are scraped one last time if they are archived
- **Automatic:** Downloading is multithreaded: multiple files download at a time to accelerate scraping
