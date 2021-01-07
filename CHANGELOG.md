# Changelog

## v3.1.0
- Better CLI support
- Breaks compatibility with v3.0.5
- Add `-u` flag to update known threads but not scrape
- Add `-p` flag to force using 4plebs for thread JSONs and attachments source

## v3.0.5
- Remove saosuite submodule since it is taking a different direction (private repo for my resources)
- Leave appropriate scripts behind for function
- Works exactly the same as v3.0.4

## v3.0.4
- Bugfix: handle HTTP error 429 from 4plebs

## v3.0.3
- Change keyword addition / deletion such that keywords are separated by commas instead of spaces
- Bugfix: Already scraped special requests saying that they have been added when trying to add again
- Optimise config saving

## v3.0.2
- Minor change to appearance
- Update .gitignore

## v3.0.1
- Fix progress bars alignment
- Decided against yuki.la scraping as the website doesn't store that many attachments, and as of today I receive 403s when trying to access it

## v3.0.0
- Major overhaul to config and code management behind the scenes using my SAO suite
- MD5 Checking: If a file already exists and its MD5 hash matches that of a file to be downloaded then the download will be skipped and the user will be informed

## v2.1.4
- Auto-updating now removed: use `git` to pull latest updates

## v2.1.3
- Bugfix for special requests ending up as 'blacklisted' (in the blacklist but still unaffected as normal)

## v2.1.2
- Blacklist now clears out opnos automatically when they are not found in the catalog

## v2.1.1
- Swanky new title display
- Add 4plebs cooldown messages
- Add error message for plebrequests made for non-4plebs boards

## v2.1.0
- Remove internal boards list dependency
- Remove v1.6.1 -> v2.0.0 config conversion code; v1 config no longer compatible with scraper, though I seem to be the only person who used v1 anyways so no worries
- Add GPL2 license

## v2.0.3
- Add /vst/ to archive boards
- Update README to acknowledge APIs

## v2.0.2
- Threads that become special requests (and special requests that become normal threads) now have their folders renamed accordingly to avoid contents being split across different folders

## v2.0.1
- Fix `PLEBREQUEST` threads appearing also in normal scrape

## v2.0.0
- Major revamp of how the config stores scraped threads: cut size of config file / search times significantly
- Fix bug of threads with same op number as a special request not being scraped regardless of board
- Removed the need for maintenance at all due to new optimised config
- When viewing scraping keywords no more quotation marks around words
- Scraper automatically detects and converts v1 config file to v2; I suspect I'm the only person using this program but at least I made it easier for myself lol
- File found in place of file being scraped is renamed as a possible duplicate instead of the scraper skipping it

## v1.6.1
- Removed `MAINTENANCE` option from main menu; maintenance is now fully automated and is only done after scraping

## v1.6.0
- Scraper now checks for updates on launch and automatically downloads them
- Additional note for changelog of v1.4.1 (number of multithreaded downloads now 4)

## v1.5.1
- Fix special requests also appearing in main scrape unnecessarily
- Additional note for changelog of v1.4.1
- Rename main program from `Bateman's 4chan Scraper.py` to `4chan Scraper.py`
- Added .gitignore stuff to repo (for my sake)

## v1.5.0
- Added `PLEBREQUEST` feature: Searches 4plebs archives for all threads with a chosen keyword in their OP on a board and adds them to special requests
- Tweaked progress bars to have less flickery cursor

## v1.4.1
- Progress bars are now aligned via padding per board (and special requests) for ease of viewing
- Removed `noarchiveboards` from the scraper config (see below)
- No longer necessary to specify if a new board has 4chan archives when adding keywords (checking if a board has an archive or not is not done at all now; special requests always directly go for the thread json, not knowing if the thread is alive or not, and for those threads that do not appear in a catalog but were scraped last time and are on a non-4chan-archive board will only produce a harmless 404 when attempting to grab the json; It is not worth coding extra if-else to avoid a few 404s; also the bug below occurred from skipping threads on non-4chan-archive but yes-4plebs-archive boards)
- Bugfix: archived threads on boards without 4chan archives that have 4plebs archives not being scraped (strictly this is only one board, /f/, however a fix nonetheless)
- Bugfix: race condition: threads from previous scrapes (in config's `lastscrapeops`) present in the catalog when the catalog json is fetched but that are archived when the thread json is fetched were scraped twice (unnecessarily)
- Change config extension from `.txt` to `.json`
- Previously scraped threads are now scraped first lest they 404 whilst newer threads are scraped
- Number of multithreaded downloads changed from 8 to 4

## v1.4.0
- Added progress bar and counter when scraping a thread

## v1.3.0
- Downloading of files is now multithreaded, by default up to 8 downloads at a time

## v1.2.1
- Maintenance is now also done automatically at the end of scraping

## v1.2.0
- Added MAINTENANCE mode: removes any duplicate numbers that may have been externally inserted into the config
- Numbers of newly scraped posts are inserted at the beginning of the config list to speed up future searches
- Changed ordering of VIEW to be consistent with SCRAPE

## v1.1.3
- Empty thumbnail folders are now removed
- Minor appearance change - reduced the number of double-line gaps in console

## v1.1.2
- 4plebs thumbnails that exist for files whose original cannot be found on 4plebs are now scraped into a subfolder of the corresponding thread folder
- Updated "HELP" text
- Optimised grabbing of JSONs by refactoring 'file list' and 'file scrape' functions to be more uniform / expandable across different APIs

## v1.1.1
- Keyword is no longer required to be specified when removing a special request thread

## v1.1.0
- Added [4plebs.org](https://www.4plebs.org) support: if a thread or file is not found on 4chan, 4plebs is then searched

## v1.0.7
- Minor code refactor

## v1.0.6
- Changed error message and "HELP" text from 'image' to 'file'
- Keyword for thread / file error is now shown along with board and no.
- Minor update to README.md

## v1.0.5
- Removed duplicate pieces of code

## v1.0.4
- Removed confusing and unnecessary text between active and archived threads during scraping
- Fixed empty folder not being deleted if corresponding thread cannot be loaded

## v1.0.3
- Minor changes to help text and 'not scraping' text
- Empty folders left after scraping are now deleted
- 'Scraping archive' text now dependent on whether known threads are in the archive

## v1.0.2
- Added text response for "DELETE" when no keywords are supplied
- Check for 404 if error occurs when grabbing image: display specific message for 404 case as well as not counting this as a 'bad' error
- Fixed config not saving when only scraping special requests and no main keywords

## v1.0.1
- Changed main menu question text "DEL" to "DELETE"
- Allowed input of "DELETE" as well as "D" and "DEL" for deleting keywords
- Changed main menu question text "BLACK" to "BLACKLIST"
- Allowed input of "BLACKLIST" as well as "B" and "BL" and "BLACK" for blacklisting
- Updated "HELP" text accordingly

## v1.0.0
- First release!
