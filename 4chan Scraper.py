
"""https://github.com/SelfAdjointOperator/4chan-Scraper"""

import urllib.request       #   getting files from web
import json                 #   config file and api pages JSONs to and from dictionary
import os                   #   managing folders
import threading            #   multiple simultaneous downloads
from time import sleep,time #   sleep if 4plebs search cooldown reached, restart delay
import argparse             #   for improved CLI

# SAO Suite imports
from saosuite import saotitle
from saosuite import saostatusmsgs
from saosuite import saoconfigmanager
from saosuite import saomd5

# Globals

lock = threading.Lock()
pm = saostatusmsgs.progressmsg()
version = '4.1.0'
boxestocheckfor = {"4chan":["name","sub","com","filename"],"4plebs":["username","subject","text","filename"]}
plebBoards = ['adv','f','hr','o','pol','s4s','sp','tg','trv','tv','x']
plebsHTTPHeader = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
numberOfDownloadThreads = 4
ConstantStrings = {
    "4chan": {
        "URL": {
            "catalogJSON": "https://a.4cdn.org/{}/catalog.json",
            "threadJSON": "https://a.4cdn.org/{}/thread/{}.json",
            "image": "https://i.4cdn.org/"
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
            "image": "https://i.4pcdn.org/"
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
            "image": "https://i.4pcdn.org/"
        },
        "DownloadMediaPost_Errors": {
            "MD5_same": "File /{}/:{}:{}:{}(thumb) already exists with same MD5 checksum; not scraping again ",
            "MD5_diff": "File /{}/:{}:{}:{}(thumb) already exists with different MD5 checksum; possible duplicate scraped ",
            "404": "File /{}/:{}:{}:{}(thumb) not found on 4plebs ",
            "error_loading": "Error: Cannot load 4plebs file /{}/:{}:{}:{}(thumb) "
        }
    }
}

################################################################################

class MediaPost():
    def __init__(self, boardcode, opno, keyword, no, tim, ext, md564):
        self.boardcode = boardcode
        self.opno = opno
        self.keyword = keyword
        self.no = no
        self.tim = tim
        self.ext = ext
        self.md564 = md564

################################################################################

def ThreadLocked(lock_object):
    """Decorator for methods to use 'with lock_object'"""
    def helper(function):
        def inner(*args,**kwargs):
            with lock_object:
                return function(*args,**kwargs)
        return inner
    return helper

################################################################################

def UpdateThreads():
    boardsNotToPrune = []
    boards = cm.valueGet("downloaded")
    nonemptyBoards_keywords = [board for board in boards if cm.tpt_getkeywords_wl("downloaded/{}".format(board))]
    for board in nonemptyBoards_keywords:
        keywords_wl = cm.tpt_getkeywords_wl("downloaded/{}".format(board))
        idnos_bl = cm.tpt_getidnos_bl("downloaded/{}".format(board))
        idnos_done = cm.tpt_getidnos_done("downloaded/{}".format(board))

        try:
            print("Getting JSON for catalog of /{}/".format(board))
            catalogJSON_url = ConstantStrings["4chan"]["URL"]["catalogJSON"].format(board)
            catalogJSON_file = urllib.request.urlopen(catalogJSON_url)
            catalogJSON = json.load(catalogJSON_file)
            blacklist_expired = [t for t in idnos_bl]

            for page in catalogJSON:
                for opPost in page["threads"]:
                    opno = opPost["no"]
                    if opno in idnos_bl:
                        blacklist_expired.remove(opno)
                        continue
                    if opno in idnos_done:
                        continue
                    boxbreak = False
                    boxestocheck = [box for box in boxestocheckfor["4chan"] if box in opPost]
                    for boxtocheck in boxestocheck:
                        for keyword in keywords_wl:
                            if keyword in opPost[boxtocheck].lower():
                                cm.tpt_promoteTaskToByIdno("downloaded/{}".format(board),opno,keyword=keyword,promotionTier="normal")
                                boxbreak = True
                                break
                        if boxbreak:
                            break
            cm.tpt_idnos_blRemove("downloaded/{}".format(board),blacklist_expired)
        except:
            boardsNotToPrune.append(board)
            print("Error: Cannot load catalog for /{}/".format(board))

    for board in boards:
        if not board in boardsNotToPrune:
            for task in cm.tpt_pruneTasks("downloaded/{}".format(board),tiers=["normal"],keywords_wl=True,idnos_bl=True,idnos_done=True)["normal"]:
                cm.ffm_rmIfEmptyTree("downloaded/{}/{} {}".format(board,str(task[0]),task[1]))

################################################################################

def Scrape(forcePlebs):
    boards = cm.valueGet("downloaded")

    # do special requests
    nonemptyBoards_special = [board for board in boards if cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")]
    if not nonemptyBoards_special:
        print("No special requests")
    else:
        print("Doing special requests")
        if forcePlebs:
            for board in nonemptyBoards_special:
                if not board in plebBoards:
                    print("Skipping board /{}/ because of --plebs flag".format(board))
                    nonemptyBoards_special.remove(board)
        ljustLength = 14
        for board in nonemptyBoards_special:
            tasks_special = cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
            ljustLength = max(ljustLength,max([14+len(board)+len(str(task[0]))+len(task[1]) for task in tasks_special]))
        for board in nonemptyBoards_special:
            tasks_special = cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
            for task in [t for t in tasks_special]:
                result = ScrapeThread(board,*task,ljustLength,forcePlebs)
                if result[0] == 'keep':
                    cm.tpt_updateTaskByIdno("downloaded/{}".format(board),task[0],result[1])
                else:
                    cm.tpt_finishTaskByIdno("downloaded/{}".format(board),task[0])

    # do normal scraping
    nonemptyBoards_keywords = [board for board in boards if cm.tpt_getkeywords_wl("downloaded/{}".format(board))]
    if not nonemptyBoards_keywords:
        print("Not scraping for any keywords")
    else:
        print("Scraping for keywords")
        for board in nonemptyBoards_keywords:
            if forcePlebs and not board in plebBoards:
                print("Skipping board /{}/ because of --plebs flag".format(board))
                continue
            print("Scraping threads from /{}/".format(board))
            tasksToScrape = cm.tpt_getTasksInTier("downloaded/{}".format(board),"normal")[:]
            ljustLength = max([14+len(board)+len(str(task[0]))+len(task[1]) for task in tasksToScrape]) if tasksToScrape else 14
            for task in tasksToScrape:
                if (result := ScrapeThread(board,*task,ljustLength,forcePlebs))[0] == 'keep':
                    cm.tpt_updateTaskByIdno("downloaded/{}".format(board),task[0],result[1])
                else:
                    cm.tpt_finishTaskByIdno("downloaded/{}".format(board),task[0])

    for board in boards:
        cm.ffm_rmIfEmptyTree("downloaded/{}".format(board))

    print("Done scraping")

################################################################################

def ScrapeThread(boardcode, threadopno, keyword, scrapednos, padding, forcePlebs):
    if not forcePlebs:
        mediaPosts = GetMediaPostsList(boardcode, threadopno, keyword, "4chan")
        filestart = 0
    if forcePlebs or mediaPosts[0] in ["try_4plebs"]:
        mediaPosts = GetMediaPostsList(boardcode, threadopno, keyword, "4plebs")
        filestart = 1
    if mediaPosts[0] in ["keep", "delete"]:
        return [mediaPosts[0], scrapednos]
    #otherwise "now_scrape"
    mediaPostsList = mediaPosts[1]

    threadDownloadFolderPath = "downloaded/{}/{} {}".format(boardcode, str(threadopno), keyword)
    cm.ffm_makedirs("{}/thumbs".format(threadDownloadFolderPath))

    #Scrape files
    pm.progressmsg(msg = "Scraping /{}/:{}:{} ".format(boardcode, str(threadopno), keyword).ljust(padding), of = len(mediaPostsList))
    keepflag = 0

    postbuffers = [[] for i in range(numberOfDownloadThreads)]
    def DownloadMediaPost_thread(dtid):
        nonlocal keepflag, postbuffers
        while True:
            with lock:
                try:
                    postbuffers[dtid] = mediaPostsList.pop(0)
                    if postbuffers[dtid].no in scrapednos:
                        pm.tick()
                        continue
                except IndexError:
                    return
            for modus in ["4chan", "4plebs", "4plebsthumbs"][filestart:]:
                result = DownloadMediaPost(threadDownloadFolderPath, postbuffers[dtid], modus)
                with lock:
                    if result == "success":
                        scrapednos.append(postbuffers[dtid].no)
                        pm.tick()
                        break
                    elif result == "keep":
                        keepflag = 1
                        break
                    elif result == "try_next_modus":
                        continue

    download_threads = [threading.Thread(target = DownloadMediaPost_thread, args=[i]) for i in range(numberOfDownloadThreads)]
    for t in download_threads:
        t.start()
    for t in download_threads:
        t.join()
    pm.finish()

    cm.ffm_rmIfEmptyTree("{}/thumbs".format(threadDownloadFolderPath))
    cm.ffm_rmIfEmptyTree(threadDownloadFolderPath)

    if keepflag == 0 and (filestart!=0 or mediaPosts[2] == True):
        return ["delete"]
    else:
        return ["keep", scrapednos]

################################################################################

def GetMediaPostsList(boardcode, threadopno, keyword, modus):
    def gmpl_error(code):
        print(ConstantStrings[modus]["GetMediaPostsList_Errors"][code].format(boardcode,str(threadopno),keyword))

    if modus == "4chan":
        try:
            threadJSON_url = ConstantStrings[modus]["URL"]["threadJSON"].format(boardcode,str(threadopno))
            threadJSON_file = urllib.request.urlopen(threadJSON_url)
            threadJSON = json.load(threadJSON_file)
            mediaPostsList = [MediaPost(boardcode, threadopno, keyword, post["no"], post["tim"], post["ext"], post["md5"]) for post in threadJSON["posts"] if "tim" in post]
            return ["now_scrape",mediaPostsList,"archived" in threadJSON["posts"][0]]
        except Exception as e:
            if hasattr(e,"code") and e.code == 404: # pylint: disable=E1101
                if boardcode in plebBoards:
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
            threadJSON_url = ConstantStrings[modus]["URL"]["threadJSON"].format(boardcode,str(threadopno))
            threadJSON_file = urllib.request.urlopen(urllib.request.Request(threadJSON_url,None,{"User-Agent":plebsHTTPHeader}))
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
                    threadJSON[str(threadopno)]["op"]["media"]["media_hash"]
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
                            postvalue["media"]["media_hash"]
                        ))
            return ["now_scrape", mediaPostsList]
        except Exception as e:
            if hasattr(e, "code") and e.code in [404, "404"]: # pylint: disable=E1101
                gmpl_error("404")
                return ["delete"]
            else:
                gmpl_error("error_loading")
                return ["keep"]

################################################################################

def DownloadMediaPost(threadDownloadFolderPath, post, modus):
    @ThreadLocked(lock)
    def sf_error(code):
        pm.progressmsg(msg = ConstantStrings[modus]["DownloadMediaPost_Errors"][code].format(post.boardcode, post.opno, post.keyword, str(post.no)))

    try:
        if modus == "4plebsthumbs":
            threadDownloadFolderPath = "{}/thumbs".format(threadDownloadFolderPath)
            imgaddress = "{}/{}.jpg".format(threadDownloadFolderPath, str(post.no))
        else:
            imgaddress = "{}/{}{}".format(threadDownloadFolderPath, str(post.no), post.ext)
        if os.path.exists(imgaddress):
            if saomd5.isHashHex(imgaddress, saomd5.base64ToHex(post.md564)):
                sf_error("MD5_same")
                return "success"
            else:
                sf_error("MD5_diff")
                rn_name, rn_ext = os.path.splitext(imgaddress)
                os.rename(imgaddress, "{}{}{}{}".format(rn_name, "_", str(int(time())), rn_ext))
        imgdomain = ConstantStrings[modus]["URL"]["image"]
        if modus == "4plebsthumbs":
            imgurl = "{}{}/{}s.jpg".format(imgdomain, post.boardcode, str(post.tim))
        else:
            imgurl = "{}{}/{}{}".format(imgdomain, post.boardcode, str(post.tim), post.ext)
        urllib.request.urlretrieve(imgurl, imgaddress)
        return "success"
    except Exception as e:
        if hasattr(e, "code") and e.code in [404, "404"]: # pylint: disable=E1101
            if modus == "4chan":
                if post.boardcode in plebBoards:
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
        help = "Print SAO logo when run")
    parser.add_argument("--update", "-u",
        action = "store_true",
        help = "Update the lists of threads to scraped, but do not scrape them now. Also prunes threads of no further interest, ie those of keywords no longer being scraped for.")
    parser.add_argument("--scrape", "-s",
        action = "store_true",
        help = "Calls --update and then scrapes")
    parser.add_argument("--plebs", "-p",
        action = "store_true",
        help = "Only use 4plebs as source of thread JSON and attachments. Affects flags --oneoff and --scrape")
    parser.add_argument("--view", "-v",
        action = "store_true",
        help = "View the current requests, keywords, and blacklist")
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

    if not any(args.__dict__.values()):
        saotitle.printLogoTitle(title = "Bateman\'s 4chan Scraper", subtitle = "Version {}".format(version))
        parser.print_help()
        raise SystemExit

    cm = saoconfigmanager.configmanager(filename = "scraperconfig.json", default = {"versioncreated":version, "downloaded":{}})
    cm.tpt_manageDirectories = True
    cm.tpt_manageDirectoriesDeleteEmptyOnUpdate = True

    if args.logo:
        saotitle.printLogoTitle(title = "Bateman\'s 4chan Scraper", subtitle = "Version {}".format(version))
    if args.view:
        someRequests = False
        for board in cm.valueGet("downloaded"):
            requests = cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
            if requests:
                if not someRequests:
                    print("Special requests:")
                    someRequests = True
                for request in requests:
                    print("/{}/:{}:{}".format(board,str(request[0]),request[1]))
        if not someRequests:
            print("No special requests")

        someKeywords = False
        for board in cm.valueGet("downloaded"):
            keywords_wl = cm.tpt_getkeywords_wl("downloaded/{}".format(board))
            if keywords_wl:
                if not someKeywords:
                    print("Keywords scraping for:")
                    someKeywords = True
                print("/{}/:".format(board),", ".join(keywords_wl))
        if not someKeywords:
            print("Not scraping any boards")

        someBlacklisted = False
        for board in cm.valueGet("downloaded"):
            idnos_bl = cm.tpt_getidnos_bl("downloaded/{}".format(board))
            if idnos_bl:
                if not someBlacklisted:
                    print("Blacklisting:")
                    someBlacklisted = True
                print("/{}/:".format(board),", ".join([str(opno) for opno in idnos_bl]))
        if not someBlacklisted:
            print("Not blacklisting any threads")
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
        if cm.tpt_getTaskTierByIdno("downloaded/{}".format(board), opno) == "special":
            keyword = cm.tpt_demoteTaskByIdno("downloaded/{}".format(board),opno)[1]
            print("Thread /{}/:{}:{} removed from special requests".format(board,str(opno),keyword))
        else:
            if cm.tpt_promoteTaskToByIdno("downloaded/{}".format(board),opno,keyword=keyword,promotionTier="special")[0]:
                print("Thread /{}/:{}:{} added to special requests".format(board,str(opno),keyword))
            else:
                print("Already scraped /{}/:{}:{}".format(board,str(opno),keyword))
        cm.save()
    if args.add:
        try:
            arg_split = args.add.split(':', 1)
            board = arg_split.pop(0)
            keywords = arg_split.pop(0).split(',')
            keywords = [t.lower().replace("_"," ").strip() for t in keywords]
            keywords = [t for t in keywords if t]
        except:
            print("Error parsing --add argument. Format must be 'boardcode:word1,word2,...,wordn'")
            raise SystemExit
        keywordsAdded = cm.tpt_keywords_wlAdd("downloaded/{}".format(board),keywords)
        keywordsNow = cm.tpt_getkeywords_wl("downloaded/{}".format(board))
        if keywordsAdded:
            print("Keywords added to /{}/: {}".format(board, ", ".join(keywordsAdded)))
        else:
            print("No keywords added to /{}/".format(board))
        if keywordsNow:
            print("Keywords for /{}/: {}".format(board, ", ".join(keywordsNow)))
        else:
            print("No keywords for /{}/ - not scraping it".format(board))
        cm.save()
    if args.delete:
        try:
            arg_split = args.delete.split(':', 1)
            board = arg_split.pop(0)
            keywords = arg_split.pop(0).split(',')
            keywords = [t.lower().replace("_"," ").strip() for t in keywords]
            keywords = [t for t in keywords if t]
        except:
            print("Error parsing --delete argument. Format must be 'boardcode:word1,word2,...,wordn'")
            raise SystemExit
        keywordsRemoved = cm.tpt_keywords_wlRemove("downloaded/{}".format(board),keywords)
        keywordsNow = cm.tpt_getkeywords_wl("downloaded/{}".format(board))
        if keywordsRemoved:
            print("Keywords removed from /{}/: {}".format(board, ", ".join(keywordsRemoved)))
        else:
            print("No keywords removed from /{}/".format(board))
        if keywordsNow:
            print("Keywords for /{}/: {}".format(board, ", ".join(keywordsNow)))
        else:
            print("No keywords for /{}/ - not scraping it".format(board))
        cm.save()
    if args.blacklist:
        try:
            arg_split = args.blacklist.split(':')
            board = arg_split.pop(0)
            opno = int(arg_split.pop(0))
        except:
            print("Error parsing --blacklist argument. Format must be 'boardcode:opno'")
            raise SystemExit
        if cm.tpt_idnos_blToggle("downloaded/{}".format(board),[opno])[0]:
            print("No longer blacklisting /{}/:{}".format(board,str(opno)))
        else:
            print("Now blacklisting /{}/:{}".format(board,str(opno)))
        cm.save()

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
        ScrapeThread(board, opno, keyword, [], 14, args.plebs)
    if args.update:
        UpdateThreads()
        cm.save()
    elif args.scrape:
        UpdateThreads()
        Scrape(args.plebs)
        cm.save()
