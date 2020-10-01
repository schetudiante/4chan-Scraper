
"""https://github.com/SelfAdjointOperator/4chan-Scraper"""

import urllib.request       #   getting files from web
import json                 #   config file and api pages jsons to and from dictionary
import os                   #   managing folders and update files
import threading            #   multiple simultaneous downloads
from time import sleep,time #   sleep if 4plebs search cooldown reached, restart delay

# SAO Suite imports
from saosuite import saotitle
from saosuite import saostatusmsgs
from saosuite import saoconfigmanager
from saosuite import saovcs
from saosuite import saomd5

version = '3.0.0'
boxestocheckfor = {"4chan":["name","sub","com","filename"],"4plebs":["username","subject","text","filename"]}
plebBoards = ['adv','f','hr','o','pol','s4s','sp','tg','trv','tv','x']
plebsHTTPHeader = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
num_download_threads = 4

################################################################################

def scrape():
    nonemptyBoards_special = [board for board in cm.valueGet("boards") if cm.tpt_getTasksInTier("boards/{}".format(board),"special")]
    if not nonemptyBoards_special:
        print("Currently no special requests")
    else:
        print("~Doing special requests~")
        requestsToDo = []
        for board in nonemptyBoards_special:
            for req in cm.tpt_getTasksInTier("boards/{}".format(board),"special"):
                if req[0] in cm.tpt_getidnos_done("boards/{}".format(board)):
                    print("Already scraped /{}/:{}:{}".format(board,str(req[0]),req[1]))
                else:
                    requestsToDo.append([board,req[0],req[1],req[2],len(board)+len(str(req[0]))+len(req[1])])
            cm.tpt_pruneTasks("boards/{}".format(board),tiers=["special"],idnos_bl=True,idnos_done=True)
        if requestsToDo:
            maxpad = max([rtd[4] for rtd in requestsToDo])
            for rtd in requestsToDo:
                rtd[4] = maxpad - rtd[4]
                result = scrapeThread(*rtd)
                if result[0] == 'keep':
                    cm.tpt_updateTask("boards/{}".format(rtd[0]),rtd[1],result[1])
                else:
                    cm.tpt_finishTask("boards/{}".format(rtd[0]),rtd[1])

    print()
    nonemptyBoards_keywords = [board for board in cm.valueGet("boards") if cm.tpt_getkeywords_wl("boards/{}".format(board))]
    if not nonemptyBoards_keywords:
        print("Currently not scraping any boards\n")
    else:
        for board in nonemptyBoards_keywords:
            finishedTasks_idnos,all_active,blacklist_expired = scrapeBoard(board,
                                                                           cm.tpt_getkeywords_wl("boards/{}".format(board)),
                                                                           cm.tpt_getidnos_bl("boards/{}".format(board)),
                                                                           [t[0] for t in cm.tpt_getTasksInTier("boards/{}".format(board),"special")],
                                                                           cm.tpt_getTasksInTier("boards/{}".format(board),"normal"),
                                                                           cm.tpt_getidnos_done("boards/{}".format(board)))
            for finishedTask_idno in finishedTasks_idnos:
                cm.tpt_finishTask("boards/{}".format(board),finishedTask_idno)
            for task in all_active:
                cm.tpt_promoteTaskTo("boards/{}".format(board),task[0],keyword=task[1],promotionTier="normal")
                cm.tpt_updateTask("boards/{}".format(board),task[0],task[2])
            cm.tpt_idnos_blRemove("boards/{}".format(board),blacklist_expired)
            print()
    print("~Updating config~")
    # saveconfig()
    print("~Config updated~")
    print("~Done scraping~")

################################################################################

def scrapeBoard(boardcode,keywords,blacklist,requestopnos,active,doneops):
    alreadyConsidered_opnos = blacklist + requestopnos + doneops

    #Check if current active are still what we want
    threadstoscrape = [t for t in active if not t[0] in alreadyConsidered_opnos and t[1] in keywords]
    alreadyConsidered_opnos += [t[0] for t in threadstoscrape]
    formerRequests = [t for t in active if t[1][:9] == '_DEMOTED_'] #TODO figure out this keyword reassignment etc
    active_return = []

    #Board Catalog JSON
    try:
        print("~Getting JSON for catalog of /{}/~".format(boardcode))
        catalogjson_url = ("https://a.4cdn.org/{}/catalog.json".format(boardcode))
        catalogjson_file = urllib.request.urlopen(catalogjson_url)
        catalogjson = json.load(catalogjson_file)
        blacklist_expired = [t for t in blacklist]
        completedOpnosReturn = []
        #Search ops not considered already
        for page in catalogjson:
            for threadop in page["threads"]:
                opno = threadop["no"]
                if opno in blacklist:
                    blacklist_expired.remove(opno)
                if not opno in alreadyConsidered_opnos:
                    boxbreak = False
                    boxestocheck=[b for b in boxestocheckfor["4chan"] if b in threadop]
                    for boxtocheck in boxestocheck:
                        for keyword in keywords:
                            if keyword in threadop[boxtocheck].lower():
                                try: #check if former request with scraped nos already
                                    formerRequest = [t for t in formerRequests if t[0] == opno][0]
                                    formerRequest_nos = formerRequest[2]
                                    try:
                                        folder_old = "{}\\{} {}".format(boardcode,str(opno),formerRequest[1][9:])
                                        folder_new = "{}\\{} {}".format(boardcode,str(opno),keyword)
                                        os.rename(folder_old,folder_new)
                                    except:
                                        pass
                                except:
                                    formerRequest_nos = []
                                threadstoscrape.append([opno,keyword,formerRequest_nos])
                                boxbreak = True
                                break
                        if boxbreak:
                            break
    except:
        print("Error: Cannot load catalog for /{}/".format(boardcode))
        blacklist_expired = []

    if threadstoscrape:
        #Compute padding for progress bar placement:
        maxsize = max([len(str(t[0]))+len(t[1]) for t in threadstoscrape])
        threadstoscrape_padded = [t+[maxsize-(len(str(t[0]))+len(t[1]))] for t in threadstoscrape]
        #Actually do the scraping now
        for ttsp in threadstoscrape_padded:
            result = scrapeThread(boardcode,*ttsp)
            if result[0] == 'keep':
                active_return.append([ttsp[0],ttsp[1],result[1]])
            else:
                completedOpnosReturn.append(ttsp[0])

    return [completedOpnosReturn,active_return,blacklist_expired]

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

    #Try to create folder
    threadaddress=("{}\\{} {}".format(boardcode,str(threadopno),keyword))
    try:
        os.makedirs(threadaddress,exist_ok=True)
    except:
        print("Error: failed to create folder '{}'".format(threadaddress))
        return ['keep',scrapednos]

    #Scrape files
    pm.progressmsg(msg="Scraping /{}/:{}:{} {}".format(boardcode,str(threadopno),keyword,' '*padding),of=len(impostslist))
    keepflag = 0

    postbuffers = [[] for i in range(num_download_threads)]
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
                if modus == '4plebsthumbs':
                    with lock:
                        try:
                            os.makedirs('{}\\thumbs'.format(threadaddress),exist_ok=True)
                        except:
                            pm.progressmsg(msg="Error: failed to create folder \'{}\\thumbs\' ".format(threadaddress))
                            keepflag = 1
                            break
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

    download_threads = [threading.Thread(target=scrapeFile_download_thread,args=[i]) for i in range(num_download_threads)]
    for t in download_threads:
        t.start()
    for t in download_threads:
        t.join()
    pm.finish()

    #Delete empty folder (or / and thumbs subfolder)
    if 'thumbs' in os.listdir(threadaddress) and not [f for f in os.listdir('{}\\thumbs'.format(threadaddress))]:
        try:
            os.rmdir('{}\\thumbs'.format(threadaddress))
        except:
            print("Error: Could not delete folder '{}\\thumbs'".format(threadaddress))
    if not [f for f in os.listdir(threadaddress)]:
        try:
            os.rmdir(threadaddress)
        except:
            print("Error: Could not delete folder '{}'".format(threadaddress))

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
            #Thread error:
            if hasattr(e,'code') and e.code == 404: # pylint: disable=E1101
                if boardcode in plebBoards:
                    #If 404 error and plebboard then try to get thread JSON from 4plebs
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
            imgaddress = "{}\\{}{}".format(threadaddress,str(post["no"]),post["ext"])
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
            imgaddress = "{}\\{}{}".format(threadaddress,str(post["no"]),post["ext"])
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
            threadaddress = '{}\\thumbs'.format(threadaddress)
            imgaddress = "{}\\{}.jpg".format(threadaddress,str(post["no"]))
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

def viewKeywords():
    someKeywords = False
    for board in cm.valueGet("boards"):
        keywords_wl = cm.tpt_getkeywords_wl("boards/{}".format(board))
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

def viewRequests():
    someRequests = False
    for board in cm.valueGet("boards"):
        requests = cm.tpt_getTasksInTier("boards/{}".format(board),"special")
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

def viewBlacklisting():
    someBlacklisted = False
    for board in cm.valueGet("boards"):
        idnos_bl = cm.tpt_getidnos_bl("boards/{}".format(board))
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

def plebRequest(boardcode,keyword):
    print("Searching 4plebs archive for threads on /{}/ containing \'{}\'".format(boardcode,keyword))
    opnos = []
    boxno = 0
    boxnos = len(boxestocheckfor["4plebs"])
    for boxtocheckfor in boxestocheckfor["4plebs"]:
        boxno += 1
        searchjson_url = 'http://archive.4plebs.org/_/api/chan/search/?type=op&boards={}&{}={}'.format(boardcode,boxtocheckfor,keyword.replace(" ","%20"))
        cooldown_loop = True
        while cooldown_loop:
            searchjson_file = urllib.request.urlopen(urllib.request.Request(searchjson_url,None,{'User-Agent':plebsHTTPHeader}))
            searchjson = json.load(searchjson_file)
            if "error" in searchjson:
                if searchjson["error"] == "No results found.":
                    cooldown_loop = False
                elif searchjson["error"].startswith("Search limit exceeded."):
                    try:
                        sleeptime = 1 + int(searchjson["error"][35:37].strip()) #35 to 37 hardcoded for time
                    except:
                        sleeptime = 30
                    print("Sleeping for {} seconds (4plebs cooldown {}/{})".format(str(sleeptime),str(boxno),str(boxnos)))
                    sleep(sleeptime)
            else:
                for post in searchjson["0"]["posts"]:
                    opnos.append(int(post["num"]))
                cooldown_loop = False

    opnos = list(set(opnos).difference(set([req[0] for req in cm.tpt_getTasksInTier("boards/{}".format(boardcode),"special")])))
    if opnos:
        opnos_len = len(opnos)
        print("Added {} special request{}".format(opnos_len,"" if opnos_len==1 else "s"))
        for opno in opnos:
            cm.tpt_promoteTaskTo("boards/{}".format(board),opno,keyword=keyword,promotionTier="special")
            print("/{}/:{}:{}".format(boardcode,str(opno),keyword))
    else:
        print("No more special requests added")

################################################################################

#Main Thread Here
lock = threading.Lock()
pm = saostatusmsgs.progressmsg()

saotitle.printLogoTitle(title="Bateman\'s 4chan Scraper",subtitle="Version {}".format(version))
cm = saoconfigmanager.configmanager(filename="scraperconfig.json",default={"versioncreated":version, "boards":{}})

if saovcs.olderThan(cm.valueGet("versioncreated"),"3.0.0"):
    # update config from v2 to v3
    for board in cm.valueGet("boards"):
        cm.denyNextFunctionSave(5)
        cm.valueMove("boards/{}/keywords".format(board),"boards/{}/keywords_wl".format(board))
        cm.valueMove("boards/{}/blacklist".format(board),"boards/{}/idnos_bl".format(board))
        cm.valueMove("boards/{}/doneops".format(board),"boards/{}/idnos_done".format(board))
        cm.valueMove("boards/{}/active".format(board),"boards/{}/tiers/normal".format(board))
        cm.valueMove("boards/{}/requests".format(board),"boards/{}/tiers/special".format(board))
    cm.valueSet("versioncreated",version)

#Main loop
while True:
    print('\n')
    action = input("What do you want to do? (SCRAPE/SCRAPEQUIT/REQUEST/PLEBREQUEST/BLACKLIST/VIEW/ADD/DELETE/HELP/QUIT) ").upper().strip()
    print('\n')

    if action in ["QUIT","Q"]:
        break

    elif action in ["HELP","H"]:
        print("This is Bateman's 4chan scraper. It saves attachments from threads whose OPs contain a keyword of interest that is being searched for. Special requests can be made. 4plebs is also sourced")
        print("The file 'scraperconfig.json' stores the program's config in the program's directory")
        print("Scraped files are saved in nested directories in the same directory as the program\n")

        print("SCRAPE      /  S: Saves files from threads whose OP contains a keyword of interest. Thread OPs from scraped threads are saved until they appear in the archive for one final thread scrape")
        print("SCRAPEQUIT  / SQ: Scrapes then closes the program")
        print("REQUEST     /  R: Toggle the scraping of a specially requested thread. Requests override the blacklist")
        print("PLEBREQUEST /  P: Searches 4plebs archives for all threads with a chosen keyword in their OP on a board and adds them to special requests")
        print("BLACKLIST   /  B: Toggle the blacklisting of a thread to not be scraped by supplying the OP number")
        print("VIEW        /  V: View the keywords that are currently being searched for")
        print("ADD         /  A: Add keywords to search for. This is per board and keywords are separated by spaces. To search for a phrase keyword eg 'American Psycho' input 'american_psycho' ")
        print("DELETE      /  D: Delete keywords to no longer search for")
        print("HELP        /  H: Shows this help text")
        print("QUIT        /  Q: Closes the program")

    elif action in ["SCRAPE","S","SCRAPEQUIT","SQ"]:
        scrape()
        if action in ["SCRAPEQUIT","SQ"]:
            break

    elif action in ["REQUEST","R"]:
        viewRequests()
        board = input("\nWhich board is the thread on? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        try:
            opno = int(input("What is the OP number of the requested thread? ").strip())
        except:
            print("Error: Invalid number")
            continue
        if cm.tpt_getTaskTier("boards/{}".format(board),opno) != "special":
            keyword = cm.tpt_sanitiseKeyword(input("What keyword(s) to tag request with? "))
            if not keyword:
                keyword = "request"
            cm.tpt_promoteTaskTo("boards/{}".format(board),opno,keyword=keyword,promotionTier="special")
            print("Thread /{}/:{}:{} added to special requests".format(board,str(opno),keyword))
        else:
            old_req_old_keyword = cm.tpt_getTaskByIdno("boards/{}".format(board),opno)[1]
            cm.tpt_demoteTask("boards/{}".format(board),opno)
            print("Thread /{}/:{}:{} removed from special requests".format(board,str(opno),old_req_old_keyword))
        # TODO: folder moving
        # try:
        #     folder_old = "{}\\{} {}".format(board,str(opno),new_request[1])
        #     folder_new = "{}\\{} {}".format(board,str(opno),keyword)
        #     os.rename(folder_old,folder_new)
        # except:
        #     pass

    elif action in ["PLEBREQUEST","P","PR"]:
        viewRequests()
        board = input("\nWhat board to search on? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        elif not board in plebBoards:
            print("/{}/ is not a 4plebs board".format(board))
            print("4plebs boards are: /{}/".format("/, /".join(plebBoards)))
            continue
        keyword = cm.tpt_sanitiseKeyword(input("What keyword to search 4plebs for? "))
        if not keyword:
            print("No keyword supplied")
            continue
        plebRequest(board,keyword)

    elif action in ["BLACKLIST","B","BLACK","BL"]:
        viewBlacklisting()
        board = input("\nWhich board is the thread on? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        try:
            blacklistopno = int(input("What is the OP number of the thread to blacklist? ").strip())
        except:
            print("Error: Invalid number")
            continue
        if cm.tpt_idnos_blToggle("boards/{}".format(board),[blacklistopno])[0]:
            print("No longer blacklisting /{}/:{}".format(board,str(blacklistopno)))
        else:
            print("Now blacklisting /{}/:{}".format(board,str(blacklistopno)))

    elif action in ["VIEW","V"]:
        viewRequests()
        print()
        viewKeywords()
        print()
        viewBlacklisting()

    elif action in ["ADD","A"]:
        viewKeywords()
        board = input("\nWhich board to add keywords to? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        keywordstoadd = input("Which keywords to start scraping for? ").lower().split()
        keywordstoadd = [keyword.replace("_"," ").strip() for keyword in keywordstoadd if keyword.replace("_"," ").strip()]
        if not cm.tpt_keywords_wlAdd("boards/{}".format(board),keywordstoadd):
            if not cm.tpt_getkeywords_wl("boards/{}".format(board)):
                print("No keywords added for /{}/, not scraping it".format(board))
            else:
                print("No more keywords added for /{}/".format(board))
        else:
            print("Keywords for /{}/ updated to:".format(board),", ".join(cm.tpt_getkeywords_wl("boards/{}".format(board))))

    elif action in ["DELETE","DEL","D"]:
        if viewKeywords() is False:
            continue
        board = input("\nWhich board to delete keywords from? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        if not cm.valuePing("boards/{}".format(board)) or not cm.tpt_getkeywords_wl("boards/{}".format(board)):
            print("Currently not scraping /{}/".format(board))
            continue
        keywordstodel = input("Which keywords to stop scraping for? ").lower().split()
        keywordstodel = [keyword.replace("_"," ").strip() for keyword in keywordstodel if keyword.replace("_"," ").strip()]
        if not cm.tpt_keywords_wlRemove("boards/{}".format(board),keywordstodel):
            print("No keywords removed for /{}/".format(board))
        elif not cm.tpt_getkeywords_wl("boards/{}".format(board)):
            print("Stopped scraping /{}/".format(board))
        else:
            print("Keywords for /{}/ updated to:".format(board),", ".join(cm.tpt_getkeywords_wl("boards/{}".format(board))))

    else:
        print("Unknown command")

################################################################################


