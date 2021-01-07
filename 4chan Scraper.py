
"""https://github.com/SelfAdjointOperator/4chan-Scraper"""

import urllib.request       #   getting files from web
import json                 #   config file and api pages jsons to and from dictionary
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
version = '3.1.0'
boxestocheckfor = {"4chan":["name","sub","com","filename"],"4plebs":["username","subject","text","filename"]}
plebBoards = ['adv','f','hr','o','pol','s4s','sp','tg','trv','tv','x']
plebsHTTPHeader = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
numberOfDownloadThreads = 4

################################################################################

def scrape():
    # do special requests
    nonemptyBoards_special = [board for board in cm.valueGet("downloaded") if cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")]
    if not nonemptyBoards_special:
        print("Currently no special requests")
    else:
        print("~Doing special requests~")
        ljustLength = 14
        for board in nonemptyBoards_special:
            try:
                ljustLength = max(ljustLength,max([14+len(board)+len(str(task[0]))+len(task[1]) for task in cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")]))
            except: # if no tasks left in tier
                pass
        for board in nonemptyBoards_special:
            for task in [t for t in cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")]:
                result = scrapeThread(board,*task,ljustLength)
                if result[0] == 'keep':
                    cm.tpt_updateTaskByIdno("downloaded/{}".format(board),task[0],result[1])
                else:
                    cm.tpt_finishTaskByIdno("downloaded/{}".format(board),task[0])
    print()

    # do normal scraping
    if not (nonemptyBoards_keywords := [board for board in cm.valueGet("downloaded") if cm.tpt_getkeywords_wl("downloaded/{}".format(board))]):
        print("Currently not scraping any boards\n")
    else:
        for board in nonemptyBoards_keywords:
            keywords_wl = cm.tpt_getkeywords_wl("downloaded/{}".format(board))
            idnos_bl = cm.tpt_getidnos_bl("downloaded/{}".format(board))
            idnos_done = cm.tpt_getidnos_done("downloaded/{}".format(board))

            #Board Catalog JSON
            try:
                print("~Getting JSON for catalog of /{}/~".format(board))
                catalogjson_url = ("https://a.4cdn.org/{}/catalog.json".format(board))
                catalogjson_file = urllib.request.urlopen(catalogjson_url)
                catalogjson = json.load(catalogjson_file)
                blacklist_expired = [t for t in idnos_bl]
                #Search ops not considered already
                for page in catalogjson:
                    for threadop in page["threads"]:
                        opno = threadop["no"]
                        if opno in idnos_bl:
                            blacklist_expired.remove(opno)
                            continue
                        if opno in idnos_done:
                            continue
                        boxbreak = False
                        boxestocheck = [box for box in boxestocheckfor["4chan"] if box in threadop]
                        for boxtocheck in boxestocheck:
                            for keyword in keywords_wl:
                                if keyword in threadop[boxtocheck].lower():
                                    cm.tpt_promoteTaskToByIdno("downloaded/{}".format(board),opno,keyword=keyword,promotionTier="normal")
                                    boxbreak = True
                                    break
                            if boxbreak:
                                break
                for task in cm.tpt_pruneTasks("downloaded/{}".format(board),tiers=["normal"],keywords_wl=True,idnos_bl=True,idnos_done=True)["normal"]:
                    cm.ffm_rmIfEmptyTree("downloaded/{}/{} {}".format(board,str(task[0]),task[1]))
                tasksToScrape = cm.tpt_getTasksInTier("downloaded/{}".format(board),"normal")[:]
                ljustLength = max([14+len(board)+len(str(task[0]))+len(task[1]) for task in tasksToScrape]) if tasksToScrape else 14
                for task in tasksToScrape:
                    if (result := scrapeThread(board,*task,ljustLength))[0] == 'keep':
                        cm.tpt_updateTaskByIdno("downloaded/{}".format(board),task[0],result[1])
                    else:
                        cm.tpt_finishTaskByIdno("downloaded/{}".format(board),task[0])
                cm.tpt_idnos_blRemove("downloaded/{}".format(board),blacklist_expired)
                print()
            except:
                print("Error: Cannot load catalog for /{}/".format(board))

    for board in cm.valueGet("downloaded"):
        cm.ffm_rmIfEmptyTree("downloaded/{}".format(board))

    print("~Done scraping~")

################################################################################

def scrapeThread(boardcode,threadopno,keyword,scrapednos,padding):
    global lock
    filelist = getFileList(boardcode,threadopno,keyword,'4chan')
    filestart = 0
    if filelist[0] in ['try_4plebs']:
        filelist = getFileList(boardcode,threadopno,keyword,'4plebs')
        filestart = 1
    if filelist[0] in ['keep','delete']:
        return [filelist[0],scrapednos]
    #otherwise 'now_scrape'
    impostslist = filelist[1]

    threadaddress=("downloaded/{}/{} {}".format(boardcode,str(threadopno),keyword))
    cm.ffm_makedirs("{}/thumbs".format(threadaddress))

    #Scrape files
    pm.progressmsg(msg="Scraping /{}/:{}:{} ".format(boardcode,str(threadopno),keyword).ljust(padding),of=len(impostslist))
    keepflag = 0

    postbuffers = [[] for i in range(numberOfDownloadThreads)]
    def scrapeFile_download_thread(dtid):
        nonlocal keepflag, postbuffers
        while True:
            with lock:
                try:
                    postbuffers[dtid] = impostslist.pop(0)
                    if postbuffers[dtid]["no"] in scrapednos:
                        pm.tick()
                        continue
                except IndexError:
                    return
            for modus in ['4chan','4plebs','4plebsthumbs'][filestart:]:
                result = scrapeFile(threadaddress,postbuffers[dtid],modus,boardcode,threadopno,keyword)
                with lock:
                    if result == 'success':
                        scrapednos.append(postbuffers[dtid]["no"])
                        pm.tick()
                        break
                    elif result == 'keep':
                        keepflag = 1
                        break
                    elif result == 'try_next_modus':
                        continue

    download_threads = [threading.Thread(target=scrapeFile_download_thread,args=[i]) for i in range(numberOfDownloadThreads)]
    for t in download_threads:
        t.start()
    for t in download_threads:
        t.join()
    pm.finish()

    cm.ffm_rmIfEmptyTree(threadaddress+"/thumbs")
    cm.ffm_rmIfEmptyTree(threadaddress)

    if keepflag == 0 and (filestart!=0 or filelist[2] == True):
        return ['delete']
    else:
        return ['keep',scrapednos]

################################################################################

def getFileList(boardcode,threadopno,keyword,modus):
    def gfl_error(num):
        gfl_errors = [
            "Thread /{}/:{}:{} not found on 4chan, trying 4plebs",
            "Thread /{}/:{}:{} not found on 4chan and not on 4plebs",
            "Error: Cannot load 4chan thread /{}/:{}:{}",
            "Thread /{}/:{}:{} not found on 4plebs",
            "Error: Cannot load 4plebs thread /{}/:{}:{}"]
        print(gfl_errors[num].format(boardcode,str(threadopno),keyword))

    if modus == '4chan':
        try:
            threadjson_url = 'https://a.4cdn.org/{}/thread/{}.json'.format(boardcode,str(threadopno))
            threadjson_file = urllib.request.urlopen(threadjson_url)
            threadjson = json.load(threadjson_file)
            impostslist = [{"no":post['no'],"tim":post['tim'],"ext":post['ext'],"md564":post['md5']} for post in threadjson["posts"] if "tim" in post]
            return ['now_scrape',impostslist,'archived' in threadjson["posts"][0]]
        except Exception as e:
            if hasattr(e,'code') and e.code == 404: # pylint: disable=E1101
                if boardcode in plebBoards:
                    gfl_error(0)
                    return ['try_4plebs']
                else:
                    gfl_error(1)
                    return ['delete']
            else:
                gfl_error(2)
                return ['keep']

    elif modus == '4plebs':
        try:
            threadjson_url = "http://archive.4plebs.org/_/api/chan/thread/?board={}&num={}".format(boardcode,str(threadopno))
            threadjson_file = urllib.request.urlopen(urllib.request.Request(threadjson_url,None,{'User-Agent':plebsHTTPHeader}))
            threadjson = json.load(threadjson_file)
            if 'error' in threadjson:
                if threadjson['error'] == 'Thread not found.':
                    raise urllib.request.HTTPError(threadjson_url,404,'error key in json','','')
                else:
                    raise Exception
            impostslist = []
            if "op" in threadjson[str(threadopno)] and threadjson[str(threadopno)]["op"]["media"] != None:
                impostslist.append({"no":int(threadjson[str(threadopno)]["op"]["num"]),"tim":os.path.splitext(threadjson[str(threadopno)]["op"]["media"]["media"])[0],"ext":os.path.splitext(threadjson[str(threadopno)]["op"]["media"]["media"])[1],"md564":threadjson[str(threadopno)]["op"]["media"]["media_hash"]})
            if "posts" in threadjson[str(threadopno)]:
                for postvalue in threadjson[str(threadopno)]["posts"].values():
                    if postvalue["media"] != None:
                        impostslist.append({"no":int(postvalue["num"]),"tim":os.path.splitext(postvalue["media"]["media"])[0],"ext":os.path.splitext(postvalue["media"]["media"])[1],"md564":postvalue["media"]["media_hash"]})
            return ['now_scrape',impostslist]
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']: # pylint: disable=E1101
                gfl_error(3)
                return ['delete']
            else:
                gfl_error(4)
                return ['keep']

################################################################################

def scrapeFile(threadaddress,post,modus,boardcode,threadopno,keyword):
    def sf_error(num):
        global lock
        sf_errors = [
            "File /{}/:{}:{}:{} already exists with different MD5 checksum; possible duplicate scraped ",
            "File /{}/:{}:{}:{} not found on 4chan, scraping 4plebs file ",
            "File /{}/:{}:{}:{} not found on 4chan and not on 4plebs ",
            "Error: Cannot load 4chan file /{}/:{}:{}:{} ",
            "File /{}/:{}:{}:{} already exists with different MD5 checksum; possible duplicate scraped ",
            "File /{}/:{}:{}:{} not found on 4plebs, scraping 4plebs thumbnail ",
            "Error: Cannot load 4plebs file /{}/:{}:{}:{} ",
            "File /{}/:{}:{}:{}(thumb) already exists with different MD5 checksum; possible duplicate scraped ",
            "File /{}/:{}:{}:{}(thumb) not found on 4plebs ",
            "Error: Cannot load 4plebs file /{}/:{}:{}:{}(thumb) ",
            "File /{}/:{}:{}:{} already exists with same MD5 checksum; not scraping again ",
            "File /{}/:{}:{}:{} already exists with same MD5 checksum; not scraping again ",
            "File /{}/:{}:{}:{}(thumb) already exists with same MD5 checksum; not scraping again "]
        with lock:
            pm.progressmsg(msg=sf_errors[num].format(boardcode,threadopno,keyword,str(post["no"])))

    if modus == '4chan':
        try:
            imgaddress = "{}/{}{}".format(threadaddress,str(post["no"]),post["ext"])
            if os.path.exists(imgaddress):
                if saomd5.isHashHex(imgaddress,saomd5.base64ToHex(post["md564"])):
                    sf_error(10)
                    return 'success'
                else:
                    sf_error(0)
                    rn_name,rn_ext = os.path.splitext(imgaddress)
                    os.rename(imgaddress,"{}{}{}{}".format(rn_name,"_",str(int(time())),rn_ext))
            imgdomain = 'https://i.4cdn.org/'
            imgurl = "{}{}/{}{}".format(imgdomain,boardcode,str(post["tim"]),post["ext"])
            urllib.request.urlretrieve(imgurl,imgaddress)
            return 'success'
        except Exception as e:
            if hasattr(e,'code') and e.code == 404: # pylint: disable=E1101
                if boardcode in plebBoards:
                    sf_error(1)
                    return 'try_next_modus'
                else:
                    sf_error(2)
                    return 'success'
            else:
                sf_error(3)
                return 'keep'

    elif modus == '4plebs':
        try:
            imgaddress = "{}/{}{}".format(threadaddress,str(post["no"]),post["ext"])
            if os.path.exists(imgaddress):
                if saomd5.isHashHex(imgaddress,saomd5.base64ToHex(post["md564"])):
                    sf_error(11)
                    return 'success'
                else:
                    sf_error(4)
                    rn_name,rn_ext = os.path.splitext(imgaddress)
                    os.rename(imgaddress,"{}{}{}{}".format(rn_name,"_",str(int(time())),rn_ext))
            imgdomain = 'https://i.4pcdn.org/'
            imgurl = "{}{}/{}{}".format(imgdomain,boardcode,str(post["tim"]),post["ext"])
            urllib.request.urlretrieve(imgurl,imgaddress)
            return 'success'
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']: # pylint: disable=E1101
                sf_error(5)
                return 'try_next_modus'
            else:
                sf_error(6)
                return 'keep'

    elif modus == '4plebsthumbs':
        try:
            threadaddress = '{}/thumbs'.format(threadaddress)
            imgaddress = "{}/{}.jpg".format(threadaddress,str(post["no"]))
            if os.path.exists(imgaddress):
                if saomd5.isHashHex(imgaddress,saomd5.base64ToHex(post["md564"])):
                    sf_error(12)
                    return 'success'
                else:
                    sf_error(7)
                    rn_name,rn_ext = os.path.splitext(imgaddress)
                    os.rename(imgaddress,"{}{}{}{}".format(rn_name,"_",str(int(time())),rn_ext))
            imgdomain = 'https://i.4pcdn.org/'
            imgurl = "{}{}/{}s.jpg".format(imgdomain,boardcode,str(post["tim"]))
            urllib.request.urlretrieve(imgurl,imgaddress)
            return 'success'
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']: # pylint: disable=E1101
                sf_error(8)
                return 'success'
            else:
                sf_error(9)
                return 'keep'

################################################################################

def viewRequests():
    someRequests = False
    for board in cm.valueGet("downloaded"):
        requests = cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")
        if requests:
            if not someRequests:
                print("Current special requests:")
                someRequests = True
            for request in requests:
                print("/{}/:{}:{}".format(board,str(request[0]),request[1]))
    if not someRequests:
        print("Currently no special requests")
        return False
    else:
        return True

################################################################################

def viewKeywords():
    someKeywords = False
    for board in cm.valueGet("downloaded"):
        keywords_wl = cm.tpt_getkeywords_wl("downloaded/{}".format(board))
        if keywords_wl:
            if not someKeywords:
                print("Currently scraping:")
                someKeywords = True
            print("/{}/:".format(board),", ".join(keywords_wl))
    if not someKeywords:
        print("Currently not scraping any boards")
        return False
    else:
        return True

################################################################################

def viewBlacklisting():
    someBlacklisted = False
    for board in cm.valueGet("downloaded"):
        idnos_bl = cm.tpt_getidnos_bl("downloaded/{}".format(board))
        if idnos_bl:
            if not someBlacklisted:
                print("Currently blacklisting:")
                someBlacklisted = True
            print("/{}/:".format(board),", ".join([str(opno) for opno in idnos_bl]))
    if not someBlacklisted:
        print("Currently not blacklisting any threads")
        return False
    else:
        return True

################################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description =
        """Download attachments from 4chan or 4plebs.
        Save attachments from threads whose OPs contain a keyword of interest that is being searched for.
        Special requests can be made.
        4plebs is also sourced.
        The file 'scraperconfig.json' stores the program's config in the program's directory.
        Scraped files are saved in nested directories in the same directory as the program.""")
    parser.add_argument("--scrape", "-s",
        action = "store_true",
        help = "Scrape now")
    parser.add_argument("--update", "-u",
        action = "store_true",
        help = "Update the lists of threads to scraped, but do not scrape them now")
    parser.add_argument("--plebs", "-p",
        action = "store_true",
        help = "Force using 4plebs as source of thread JSON and attachments")
    parser.add_argument("--view", "-v",
        action = "store_true",
        help = "View the current requests, keywords, and blacklist")
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
        saotitle.printLogoTitle(title = "Bateman\'s 4chan Scraper", subtitle = "Version {}".format(version), newline = False)
        parser.print_help()
        raise SystemExit

    cm = saoconfigmanager.configmanager(filename = "scraperconfig.json", default = {"versioncreated":version, "downloaded":{}})
    cm.tpt_manageDirectories = True
    cm.tpt_manageDirectoriesDeleteEmptyOnUpdate = True

    # print("P  / PLEBREQUEST: Searches 4plebs archives for all threads with a chosen keyword in their OP on a board and adds them to special requests.") TODO

    if args.view:
        viewRequests()
        print()
        viewKeywords()
        print()
        viewBlacklisting()
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
            print("Current keywords for /{}/: {}".format(board, ", ".join(keywordsNow)))
        else:
            print("Currently no keywords for /{}/ - not scraping it".format(board))
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
            print("Current keywords for /{}/: {}".format(board, ", ".join(keywordsNow)))
        else:
            print("Currently no keywords for /{}/ - not scraping it".format(board))
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

    if args.update:
        pass # TODO
    elif args.scrape:
        scrape()
        cm.save()

    def pleb():
        pass
        # elif action in ["PLEBREQUEST","P","PR"]:
        #     viewRequests()
        #     board = input("\nWhat board to search on? ").lower().strip()
        #     if not board:
        #         print("No board supplied")
        #         continue
        #     elif not board in plebBoards:
        #         print("/{}/ is not a 4plebs board".format(board))
        #         print("4plebs boards are: /{}/".format("/, /".join(plebBoards)))
        #         continue
        #     keyword = cm.tpt_sanitiseKeyword(input("What keyword to search 4plebs for? "))
        #     if not keyword:
        #         print("No keyword supplied")
        #         continue
        #     print("Searching 4plebs archive for threads on /{}/ containing \'{}\'".format(board,keyword))
        #     opnos = []
        #     boxno = 0
        #     boxnos = len(boxestocheckfor["4plebs"])
        #     for boxtocheckfor in boxestocheckfor["4plebs"]:
        #         boxno += 1
        #         searchjson_url = 'http://archive.4plebs.org/_/api/chan/search/?type=op&boards={}&{}={}'.format(board,boxtocheckfor,keyword.replace(" ","%20"))
        #         cooldown_loop = True
        #         while cooldown_loop:
        #             try:
        #                 searchjson_file = urllib.request.urlopen(urllib.request.Request(searchjson_url,None,{'User-Agent':plebsHTTPHeader}))
        #                 searchjson = json.load(searchjson_file)
        #                 if "error" in searchjson:
        #                     if searchjson["error"] != "No results found.":
        #                         print("Error loading 4plebs JSON")
        #                 else:
        #                     for post in searchjson["0"]["posts"]:
        #                         opnos.append(int(post["num"]))
        #                 cooldown_loop = False
        #             except urllib.request.HTTPError as e:
        #                 if e.code == 429:
        #                     try:
        #                         sleeptime = int(json.loads(e.readline().decode("utf-8"))["error"][35:37].strip())
        #                     except:
        #                         sleeptime = 15
        #                     print("Trying again in {} seconds (HTTP error 429 cooldown {}/{})".format(str(sleeptime),str(boxno),str(boxnos)))
        #                     sleep(sleeptime)
        #                 else:
        #                     print("Error loading 4plebs JSON")

        #     opnos = list(set(opnos).difference(set([req[0] for req in cm.tpt_getTasksInTier("downloaded/{}".format(board),"special")])))
        #     if opnos:
        #         opnos_len = len(opnos)
        #         print("Found {} more thread{}".format(opnos_len,"" if opnos_len==1 else "s"))
        #         for opno in opnos:
        #             if cm.tpt_promoteTaskToByIdno("downloaded/{}".format(board),opno,keyword=keyword,promotionTier="special")[0]:
        #                 print("Thread /{}/:{}:{} added to special requests".format(board,str(opno),keyword))
        #             else:
        #                 print("Already scraped /{}/:{}:{}".format(board,str(opno),keyword))
        #     else:
        #         print("No more special requests added")
        #     cm.save()
