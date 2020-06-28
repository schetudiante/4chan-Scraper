# Changelog

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
