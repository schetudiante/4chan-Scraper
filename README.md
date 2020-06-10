# Bateman's 4chan Scraper

This is Bateman's 4chan image scraper. It is a command line based program that saves images from threads on [4chan.org](https://www.4chan.org) whose OPs contain a keyword the user is interested in. Special thread requests can also be made.

### Files

The main program to run is `Bateman's 4chan Scraper.py`, written in Python 3.6. When run the program will create a config file `scraperconfig.txt` in the current directory, and images scraped will be saved in folders alongside the program.

### Features

- Add and remove boards with their own set of keywords to scrape for
- Make special requests to scrape custom threads 
- Blacklist threads to not scrape
- View what keywords are being scraped for, special requests are being made, and blacklisted threads
- Option to auto-quit once the current scraping session has finished
- Inbuilt `HELP` command
- **Automatic:** Threads are scraped one last time if they are archived
