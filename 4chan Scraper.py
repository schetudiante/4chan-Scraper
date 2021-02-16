
"""https://github.com/SelfAdjointOperator/4chan-Scraper"""

import urllib.request       #   getting files from web
import json                 #   config file and api pages JSONs to and from dictionary
import os                   #   managing folders
import threading            #   multiple simultaneous downloads
from time import sleep,time #   sleep if 4plebs search cooldown reached, restart delay
import argparse             #   for improved CLI
import re                   #   regex for filename formatting

# SAO Suite imports
from saosuite import saotitle
from saosuite import saostatusmsgs
from saosuite import saoconfigmanager
from saosuite import saomd5

GLOBAL_version = "4.0.2dev"

class MediaPost():
    def __init__(self, boardcode, opno, keyword, no, tim, ext, md5Hex):
        self.boardcode = boardcode
        self.opno = opno
        self.keyword = keyword
        self.no = no
        self.tim = tim
        self.ext = ext
        self.md5Hex = md5Hex

class Scraper():
    boxesToCheckFor = {"4chan":["name","sub","com","filename"],"4plebs":["username","subject","text","filename"]}
    plebBoards = ['adv','f','hr','o','pol','s4s','sp','tg','trv','tv','x']
    constantStrings = {
        "4chan": {
            "URL": {
                "catalogJSON": "https://a.4cdn.org/{}/catalog.json",
                "threadJSON": "https://a.4cdn.org/{}/thread/{}.json",
                "image": "https://i.4cdn.org/{}/{}{}"
            },
            "GetMediaPostsList_Errors": {
                "404": "Thread /{}/:{}:{} not found on 4chan, trying 4plebs",
                "404_no_4plebs": "Thread /{}/:{}:{} not found on 4chan and not on 4plebs",
                "error_loading": "Error: Cannot load 4chan thread /{}/:{}:{}"
            },
            "DownloadMediaPost_Errors": {
                "MD5_same": "File /{}/:{}:{}:{} already exists with same MD5 checksum; not scraping again ",
                "MD5_diff": "File /{}/:{}:{}:{} already exists with different MD5 checksum; possible duplicate scraped ",
                "404": "File /{}/:{}:{}:{} not found on 4chan, scraping 4plebs file ",
                "404_no_4plebs": "File /{}/:{}:{}:{} not found on 4chan and not on 4plebs ",
                "error_loading": "Error: Cannot load 4chan file /{}/:{}:{}:{} "
            }
        },
        "4plebs": {
            "URL": {
                "threadJSON": "http://archive.4plebs.org/_/api/chan/thread/?board={}&num={}",
                "image": "https://i.4pcdn.org/{}/{}{}"
            },
            "GetMediaPostsList_Errors": {
                "404": "Thread /{}/:{}:{} not found on 4plebs",
                "error_loading": "Error: Cannot load 4plebs thread /{}/:{}:{}"
            },
            "DownloadMediaPost_Errors": {
                "MD5_same": "File /{}/:{}:{}:{} already exists with same MD5 checksum; not scraping again ",
                "MD5_diff": "File /{}/:{}:{}:{} already exists with different MD5 checksum; possible duplicate scraped ",
                "404": "File /{}/:{}:{}:{} not found on 4plebs, scraping 4plebs thumbnail ",
                "error_loading": "Error: Cannot load 4plebs file /{}/:{}:{}:{} "
            }
        },
        "4plebsthumbs": {
            "URL": {
                "image": "https://i.4pcdn.org/{}/{}s{}"
            },
            "DownloadMediaPost_Errors": {
                "MD5_same": "File /{}/:{}:{}:{}(thumb) already exists with same MD5 checksum; not scraping again ",
                "MD5_diff": "File /{}/:{}:{}:{}(thumb) already exists with different MD5 checksum; possible duplicate scraped ",
                "404": "File /{}/:{}:{}:{}(thumb) not found on 4plebs ",
                "error_loading": "Error: Cannot load 4plebs file /{}/:{}:{}:{}(thumb) "
            }
        }
    }
    def __init__(self, configVersion, filenameFormat, forcePlebs = False, numberOfDownloadThreads = 1):
        self.lock = threading.Lock()
        self.cm = saoconfigmanager.configmanager(filename = "scraperconfig.json", default = {"versioncreated": configVersion, "downloaded": {}})

        self.filenameFormat = os.path.normpath(filenameFormat)
        self.forcePlebs = forcePlebs
        self.numberOfDownloadThreads = numberOfDownloadThreads

    def ViewRequests(self):
        someRequests = False
        for board in self.cm.valueGet("downloaded"):
            requests = self.cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
            if requests:
                if not someRequests:
                    print("Current special requests:")
                    someRequests = True
                for request in requests:
                    print("/{}/:{}:{}".format(board,str(request[0]),request[1]))
        if not someRequests:
            print("Currently no special requests")

    def ViewKeywords(self):
        someKeywords = False
        for board in self.cm.valueGet("downloaded"):
            keywords_wl = self.cm.tpt_getkeywords_wl("downloaded/{}".format(board))
            if keywords_wl:
                if not someKeywords:
                    print("Currently scraping:")
                    someKeywords = True
                print("/{}/:".format(board),", ".join(keywords_wl))
        if not someKeywords:
            print("Currently not scraping any boards")

    def ViewBlacklisting(self):
        someBlacklisted = False
        for board in self.cm.valueGet("downloaded"):
            idnos_bl = self.cm.tpt_getidnos_bl("downloaded/{}".format(board))
            if idnos_bl:
                if not someBlacklisted:
                    print("Currently blacklisting:")
                    someBlacklisted = True
                print("/{}/:".format(board),", ".join([str(opno) for opno in idnos_bl]))
        if not someBlacklisted:
            print("Currently not blacklisting any threads")

    def SaveConfig(self):
        self.cm.save()

    def UpdateThreads(self):
        boardsNotToPrune = []
        boards = self.cm.valueGet("downloaded")
        nonemptyBoards_keywords = [board for board in boards if self.cm.tpt_getkeywords_wl("downloaded/{}".format(board))]
        for board in nonemptyBoards_keywords:
            keywords_wl = self.cm.tpt_getkeywords_wl("downloaded/{}".format(board))
            idnos_bl = self.cm.tpt_getidnos_bl("downloaded/{}".format(board))
            idnos_done = self.cm.tpt_getidnos_done("downloaded/{}".format(board))

            try:
                print("Getting JSON for catalog of /{}/".format(board))
                catalogJSON_url = self.constantStrings["4chan"]["URL"]["catalogJSON"].format(board)
                catalogJSON_file = urllib.request.urlopen(catalogJSON_url)
                catalogJSON = json.load(catalogJSON_file)
                blacklist_expired = idnos_bl[:]

                for page in catalogJSON:
                    for opPost in page["threads"]:
                        opno = opPost["no"]
                        if opno in idnos_bl:
                            blacklist_expired.remove(opno)
                            continue
                        if opno in idnos_done:
                            continue
                        boxbreak = False
                        boxestocheck = [box for box in self.boxesToCheckFor["4chan"] if box in opPost]
                        for boxtocheck in boxestocheck:
                            for keyword in keywords_wl:
                                if keyword in opPost[boxtocheck].lower():
                                    self.cm.tpt_promoteTaskToByIdno("downloaded/{}".format(board),opno,keyword=keyword,promotionTier="normal")
                                    boxbreak = True
                                    break
                            if boxbreak:
                                break
                self.cm.tpt_idnos_blRemove("downloaded/{}".format(board), blacklist_expired)
            except:
                boardsNotToPrune.append(board)
                print("Error: Cannot load catalog for /{}/".format(board))

        for board in boards:
            if not board in boardsNotToPrune:
                self.cm.tpt_pruneTasks("downloaded/{}".format(board), tiers = ["normal"], keywords_wl = True, idnos_bl = True, idnos_done = True)["normal"]

    def Scrape(self):
        boards = self.cm.valueGet("downloaded")

        # do special requests
        nonemptyBoards_special = [board for board in boards if self.cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")]
        if not nonemptyBoards_special:
            print("No special requests")
        else:
            print("Doing special requests")
            ljustLength = 14
            for board in nonemptyBoards_special:
                tasks_special = self.cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
                ljustLength = max(ljustLength,max([14+len(board)+len(str(task[0]))+len(task[1]) for task in tasks_special]))
            for board in nonemptyBoards_special:
                tasks_special = self.cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
                for task in [t for t in tasks_special]:
                    result = self.ScrapeThread(board,*task,ljustLength)
                    if result[0] == 'keep':
                        self.cm.tpt_updateTaskByIdno("downloaded/{}".format(board),task[0],result[1])
                    else:
                        self.cm.tpt_finishTaskByIdno("downloaded/{}".format(board),task[0])

        # do normal scraping
        nonemptyBoards_keywords = [board for board in boards if self.cm.tpt_getkeywords_wl("downloaded/{}".format(board))]
        if not nonemptyBoards_keywords:
            print("Not scraping for any keywords")
        else:
            print("Scraping for keywords")
            for board in nonemptyBoards_keywords:
                print("Scraping threads from /{}/".format(board))
                tasksToScrape = self.cm.tpt_getTasksInTier("downloaded/{}".format(board),"normal")[:]
                ljustLength = max([14 + len(board) + len(str(task[0])) + len(task[1]) for task in tasksToScrape]) if tasksToScrape else 14
                for task in tasksToScrape:
                    if (result := self.ScrapeThread(board,*task,ljustLength))[0] == 'keep':
                        self.cm.tpt_updateTaskByIdno("downloaded/{}".format(board),task[0],result[1])
                    else:
                        self.cm.tpt_finishTaskByIdno("downloaded/{}".format(board),task[0])

        print("Done scraping")

    def ScrapeThread(self, boardcode, threadopno, keyword, scrapednos, padding):
        if boardcode in self.plebBoards:
            if self.forcePlebs:
                sitesToCheck_mediaPosts = ["4plebs"]
                sitesToCheck_mediaFiles = ["4plebs", "4plebsthumbs"]
            else:
                sitesToCheck_mediaPosts = ["4chan", "4plebs"]
                sitesToCheck_mediaFiles = ["4chan", "4plebs", "4plebsthumbs"]
        else:
            sitesToCheck_mediaPosts = ["4chan"]
            sitesToCheck_mediaFiles = ["4chan"]

        no_4chan_yes_4plebs = False

        for index, modus in enumerate(sitesToCheck_mediaPosts):
            mediaPosts = self.GetMediaPostsList(boardcode, threadopno, keyword, modus)
            if mediaPosts[0] in ["keep", "delete"]:
                return [mediaPosts[0], scrapednos]
            elif mediaPosts[0] in ["try_4plebs"]:
                no_4chan_yes_4plebs = True
            elif mediaPosts[0] in ["now_scrape"]:
                mediaPostsList = mediaPosts[1]
                sitesToCheck_mediaFiles = sitesToCheck_mediaFiles[index:]
                break

        #Scrape files
        pm = saostatusmsgs.ProgressMessage(message = "Scraping /{}/:{}:{} ".format(boardcode, str(threadopno), keyword).ljust(padding), of = len(mediaPostsList))
        anyDownloadErrors = False

        def DownloadMediaPost_thread():
            nonlocal anyDownloadErrors, scrapednos, pm
            while True:
                with self.lock:
                    try:
                        post = mediaPostsList.pop(0)
                        if post.no in scrapednos:
                            pm.tick()
                            continue
                    except IndexError:
                        return
                for modus in sitesToCheck_mediaFiles:
                    result = self.DownloadMediaPost(post, modus, pm)
                    with self.lock:
                        if result == "success":
                            scrapednos.append(post.no)
                            pm.tick()
                            break
                        elif result == "keep":
                            anyDownloadErrors = True
                            break
                        elif result == "try_next_modus":
                            continue

        download_threads = [threading.Thread(target = DownloadMediaPost_thread) for _ in range(self.numberOfDownloadThreads)]
        for t in download_threads:
            t.start()
        for t in download_threads:
            t.join()
        pm.finish()

        if (not anyDownloadErrors) and (no_4chan_yes_4plebs or (mediaPosts[2] == True)):
            return ["delete"]
        else:
            return ["keep", scrapednos]

    def GetMediaPostsList(self, boardcode, threadopno, keyword, modus):
        def gmpl_error(code):
            print(self.constantStrings[modus]["GetMediaPostsList_Errors"][code].format(boardcode,str(threadopno),keyword))

        if modus == "4chan":
            try:
                threadJSON_url = self.constantStrings[modus]["URL"]["threadJSON"].format(boardcode,str(threadopno))
                threadJSON_file = urllib.request.urlopen(threadJSON_url)
                threadJSON = json.load(threadJSON_file)
                mediaPostsList = [MediaPost(boardcode, threadopno, keyword, post["no"], post["tim"], post["ext"], saomd5.base64ToHex(post["md5"])) for post in threadJSON["posts"] if "tim" in post]
                return ["now_scrape", mediaPostsList, "archived" in threadJSON["posts"][0]]
            except Exception as e:
                if hasattr(e,"code") and e.code == 404: # pylint: disable=E1101
                    if boardcode in self.plebBoards:
                        gmpl_error("404")
                        return ["try_4plebs"]
                    else:
                        gmpl_error("404_no_4plebs")
                        return ["delete"]
                else:
                    gmpl_error("error_loading")
                    return ["keep"]

        elif modus == "4plebs":
            try:
                threadJSON_url = self.constantStrings[modus]["URL"]["threadJSON"].format(boardcode,str(threadopno))
                threadJSON_file = urllib.request.urlopen(urllib.request.Request(threadJSON_url,None,{"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"}))
                threadJSON = json.load(threadJSON_file)
                if "error" in threadJSON:
                    if threadJSON["error"] == "Thread not found.":
                        raise urllib.request.HTTPError(threadJSON_url,404,"error key in JSON","","")
                    else:
                        raise Exception
                mediaPostsList = []
                if "op" in threadJSON[str(threadopno)] and threadJSON[str(threadopno)]["op"]["media"] != None:
                    mediaPostsList.append(MediaPost(
                        boardcode,
                        threadopno,
                        keyword,
                        threadopno,
                        os.path.splitext(threadJSON[str(threadopno)]["op"]["media"]["media"])[0],
                        os.path.splitext(threadJSON[str(threadopno)]["op"]["media"]["media"])[1],
                        saomd5.base64ToHex(threadJSON[str(threadopno)]["op"]["media"]["media_hash"])
                    ))
                if "posts" in threadJSON[str(threadopno)]:
                    for postvalue in threadJSON[str(threadopno)]["posts"].values():
                        if postvalue["media"] != None:
                            mediaPostsList.append(MediaPost(
                                boardcode,
                                threadopno,
                                keyword,
                                int(postvalue["num"]),
                                os.path.splitext(postvalue["media"]["media"])[0],
                                os.path.splitext(postvalue["media"]["media"])[1],
                                saomd5.base64ToHex(postvalue["media"]["media_hash"])
                            ))
                return ["now_scrape", mediaPostsList, False] # 4plebs JSONs do not tell us if a thread is archived; always assume not if forceplebs or falling back to 4plebs from 4chan
            except Exception as e:
                if hasattr(e, "code") and e.code in [404, "404"]: # pylint: disable=E1101
                    gmpl_error("404")
                    return ["delete"]
                else:
                    gmpl_error("error_loading")
                    return ["keep"]

    def DownloadMediaPost(self, post, modus, pm):
        # threadDownloadFolderPath = "downloaded/{}/{} {}".format(boardcode, str(threadopno), keyword)
        def sf_error(code):
            with self.lock:
                pm.printMessage(self.constantStrings[modus]["DownloadMediaPost_Errors"][code].format(post.boardcode, post.opno, post.keyword, str(post.no)))

        regExpression = r"%\((?P<field>{})\)s".format("|".join(post.__dict__.keys())) # TODO allow more keys eg modus
        downloadPath = re.sub(regExpression, lambda match: str(post.__dict__[match.group("field")]), self.filenameFormat)

        if (foldersPath := os.path.split(downloadPath)[0]):
            os.makedirs(foldersPath, exist_ok = True)

        if os.path.exists(downloadPath):
            if saomd5.isHashHex(downloadPath, post.md5Hex):
                sf_error("MD5_same")
                return "success"
            else:
                sf_error("MD5_diff")
                rn_name, rn_ext = os.path.splitext(downloadPath)
                os.rename(downloadPath, "{}_{}{}".format(rn_name, str(int(time())), rn_ext))

        try:
            imgurl = self.constantStrings[modus]["URL"]["image"].format(post.boardcode, str(post.tim), post.ext)
            urllib.request.urlretrieve(imgurl, downloadPath)
            return "success"
        except Exception as e:
            if hasattr(e, "code") and e.code in [404, "404"]: # pylint: disable=E1101
                if modus == "4chan":
                    if post.boardcode in self.plebBoards:
                        sf_error("404")
                        return "try_next_modus"
                    else:
                        sf_error("404_no_4plebs")
                        return "success"
                elif modus == "4plebs":
                    sf_error("404")
                    return "try_next_modus"
                elif modus == "4plebsthumbs":
                    sf_error("404")
                    return "success"
            else:
                sf_error("error_loading")
                return "keep"

################################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description =
        """Download attachments from 4chan or 4plebs.
        Save attachments from threads whose OPs contain a keyword of interest that is being searched for.
        Special requests can be made.
        4plebs is also sourced.
        The file 'scraperconfig.json' stores the program's config in the program's directory.
        Scraped files are saved in nested directories in the same directory as the program.""")
    parser.add_argument("--logo", "-l",
        action = "store_true",
        help = "Print SAO logo and program version")
    parser.add_argument("--update", "-u",
        action = "store_true",
        help = "Update the lists of threads to scraped, but do not scrape them now. Also prunes threads of no further interest, ie those of keywords no longer being scraped for.")
    parser.add_argument("--scrape", "-s",
        action = "store_true",
        help = "Calls --update and then scrapes")
    parser.add_argument("--plebs", "-p",
        action = "store_true",
        help = "Force the use of 4plebs as the source of thread JSON and attachments for pleb boards. Affects flags --oneoff and --scrape")
    parser.add_argument("--view", "-v",
        action = "store_true",
        help = "View the current requests, keywords, and blacklist")
    parser.add_argument("--filename", "-f",
        action = "store",
        help = "Specify the format of download filenames: default is '{}'. A full list of formatting parameters can be found in the README.md".format(os.path.normpath("./downloaded/%(boardcode)s/%(opno)s %(keyword)s/%(no)s%(ext)s".replace("%", "%%"))),
        default = "{}".format(os.path.normpath("./downloaded/%(boardcode)s/%(opno)s %(keyword)s/%(no)s%(ext)s")))
    parser.add_argument("--oneoff", "-o",
        action = "store",
        help = "Perform a oneoff scrape of a specified thread of the form 'boardcode:opno:tag'. This ignores the config, whether the thread has been scraped before or not, or is blacklisted etc. 'tag' is optional, by default it is 'oneoff'")
    parser.add_argument("--request", "-r",
        action = "store",
        help = "Toggle the scraping of a specially requested thread in the form 'boardcode:opno:tag'. This overrides the blacklist. 'tag' is optional, by default it is 'request'")
    parser.add_argument("--add", "-a",
        action = "store",
        help = "Add keywords to scrape for in the form 'boardcode:word1,word2,...,wordn'")
    parser.add_argument("--delete", "-d",
        action = "store",
        help = "Delete keywords to no longer search for in the form 'boardcode:word1,word2,...,wordn'")
    parser.add_argument("--blacklist", "-b",
        action = "store",
        help = "Toggle the blacklisting of a thread to not be scraped in the form 'boardcode:opno'")
    args = parser.parse_args()

    scraper = Scraper(GLOBAL_version, args.filename, forcePlebs = args.plebs, numberOfDownloadThreads = 4)

    if args.logo:
        saotitle.printLogoTitle(title = "Bateman\'s 4chan Scraper", subtitle = "Version {}".format(GLOBAL_version))
    if args.view:
        scraper.ViewRequests()
        scraper.ViewKeywords()
        scraper.ViewBlacklisting()
    if args.request:
        try:
            arg_split = args.request.split(':', 2)
            board = arg_split.pop(0)
            opno = int(arg_split.pop(0))
        except:
            print("Error parsing --request argument. Format must be 'boardcode:opno:tag' where 'tag' is optional")
            raise SystemExit
        try:
            keyword = arg_split.pop(0)
        except IndexError:
            keyword = "request"
        if scraper.cm.tpt_getTaskTierByIdno("downloaded/{}".format(board), opno) == "special":
            keyword = scraper.cm.tpt_demoteTaskByIdno("downloaded/{}".format(board), opno)[1]
            print("Thread /{}/:{}:{} removed from special requests".format(board, str(opno), keyword))
        else:
            if scraper.cm.tpt_promoteTaskToByIdno("downloaded/{}".format(board), opno, keyword = keyword, promotionTier = "special")[0]:
                print("Thread /{}/:{}:{} added to special requests".format(board, str(opno), keyword))
            else:
                print("Already scraped /{}/:{}:{}".format(board, str(opno), keyword))
        scraper.SaveConfig()
    if args.add:
        try:
            arg_split = args.add.split(':', 1)
            board = arg_split.pop(0)
            keywords = arg_split.pop(0).split(',')
        except:
            print("Error parsing --add argument. Format must be 'boardcode:word1,word2,...,wordn'")
            raise SystemExit
        keywordsAdded = scraper.cm.tpt_keywords_wlAdd("downloaded/{}".format(board),keywords)
        keywordsNow = scraper.cm.tpt_getkeywords_wl("downloaded/{}".format(board))
        if keywordsAdded:
            print("Keywords added to /{}/: {}".format(board, ", ".join(keywordsAdded)))
        else:
            print("No keywords added to /{}/".format(board))
        if keywordsNow:
            print("Keywords for /{}/: {}".format(board, ", ".join(keywordsNow)))
        else:
            print("No keywords for /{}/ - not scraping it".format(board))
        scraper.SaveConfig()
    if args.delete:
        try:
            arg_split = args.delete.split(':', 1)
            board = arg_split.pop(0)
            keywords = arg_split.pop(0).split(',')
        except:
            print("Error parsing --delete argument. Format must be 'boardcode:word1,word2,...,wordn'")
            raise SystemExit
        keywordsRemoved = scraper.cm.tpt_keywords_wlRemove("downloaded/{}".format(board),keywords)
        keywordsNow = scraper.cm.tpt_getkeywords_wl("downloaded/{}".format(board))
        if keywordsRemoved:
            print("Keywords removed from /{}/: {}".format(board, ", ".join(keywordsRemoved)))
        else:
            print("No keywords removed from /{}/".format(board))
        if keywordsNow:
            print("Keywords for /{}/: {}".format(board, ", ".join(keywordsNow)))
        else:
            print("No keywords for /{}/ - not scraping it".format(board))
        scraper.SaveConfig()
    if args.blacklist:
        try:
            arg_split = args.blacklist.split(':')
            board = arg_split.pop(0)
            opno = int(arg_split.pop(0))
        except:
            print("Error parsing --blacklist argument. Format must be 'boardcode:opno'")
            raise SystemExit
        if scraper.cm.tpt_idnos_blToggle("downloaded/{}".format(board),[opno])[0]:
            print("No longer blacklisting /{}/:{}".format(board,str(opno)))
        else:
            print("Now blacklisting /{}/:{}".format(board,str(opno)))
        scraper.SaveConfig()

    if args.oneoff:
        try:
            arg_split = args.oneoff.split(':', 2)
            board = arg_split.pop(0)
            opno = int(arg_split.pop(0))
        except:
            print("Error parsing --oneoff argument. Format must be 'boardcode:opno:tag' where 'tag' is optional")
            raise SystemExit
        try:
            keyword = arg_split.pop(0)
        except IndexError:
            keyword = "oneoff"
        scraper.ScrapeThread(board, opno, keyword, [], 14)
    if args.update:
        scraper.UpdateThreads()
        scraper.SaveConfig()
    if args.scrape:
        scraper.UpdateThreads()
        scraper.Scrape()
        scraper.SaveConfig()
