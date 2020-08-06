##################################
#####BATEMAN'S 4CHAN SCRAPER######
##################################
##github.com/SelfAdjointOperator##
##################################

import urllib.request   #   getting files from web
import json             #   config file and api pages jsons to and from dictionary
import os               #   managing folders and update files
import threading        #   multiple simultaneous downloads
from sys import stdout  #   for progress bar
from time import sleep  #   sleep if 4plebs search cooldown reached, restart delay

version = '2.0.0beta'
auto_update = False # set to False during maintenance / developing
boxestocheckfor = {"4chan":["name","sub","com","filename"],"4plebs":["username","subject","text","filename"]}
no4chanArchiveBoards = ["b","bant","f","trash"] # unused, probably not implementing ifelse ifelse ifelse to save a couple of 404s
                                                # may also skip some still alive threads that have just dropped off the catalog
plebboards = ['adv','f','hr','o','pol','s4s','sp','tg','trv','tv','x']
plebsHTTPHeader = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
num_download_threads = 4

################################################################################

def new_config():
    global version
    # v1configjson = {"keywords": {}, "lastscrapeops": {}, "specialrequests": [], "blacklistedopnos": {}, "scrapednos": {}}
    # v2aconfigjson = {"version": version, "keywords": {}, "specialrequests": [], "blacklistedopnos": {}, "scrapednos": {}}
    return {"version_created":version, "boards":{}}

################################################################################

def possible_new_board(boardcode):
    if not boardcode in configjson["boards"]:
        configjson["boards"][boardcode] = {"keywords":[], "blacklist":[], "requests":[], "active":[], "doneops":[]}

################################################################################

def scrape():
    if not configjson["specialrequests"]:
        print("Currently no special requests")
    else:
        print("~Doing special requests~")
        for req in configjson["specialrequests"]:
            if req[1] in configjson["scrapednos"][req[0]]["doneops"]:
                print("Already scraped /{}/:{}:{}".format(req[0],str(req[1]),req[2]))
        configjson["specialrequests"] = [req for req in configjson["specialrequests"] if not req[1] in configjson["scrapednos"][req[0]]["doneops"]]
        maxsize = max([len(srq[0])+len(str(srq[1]))+len(srq[2]) for srq in configjson["specialrequests"]])
        srqs_padded = [srq+[maxsize-(len(srq[0])+len(str(srq[1]))+len(srq[2]))] for srq in configjson["specialrequests"]]
        configjson["specialrequests"] = []
        for srqp in srqs_padded:
            result = scrapethread(*srqp)
            if result[0] == 'keep':
                configjson["specialrequests"].append([srqp[0],srqp[1],srqp[2],result[1]])
            else:
                configjson["scrapednos"][srqp[0]]["doneops"].insert(0,srqp[1])

    print()
    if not configjson["keywords"]:
        print("Currently not scraping any boards\n")
    else:
        for boardcode in configjson["keywords"]:
            configjson["scrapednos"][boardcode] = scrapeboard(configjson["scrapednos"][boardcode],boardcode,configjson["keywords"][boardcode],configjson["blacklistedopnos"][boardcode]+[srq[1] for srq in configjson["specialrequests"] if srq[0] == boardcode])
            print()
    print("~Updating config~")
    saveconfig()
    print("~Config updated~")
    print("~Done scraping~")

################################################################################

def scrapeboard(scrapednosdic,boardcode,keywords,ignoreops):
    global boxestocheckfor
    threadstoscrape = [t for t in scrapednosdic["active"] if not t[0] in ignoreops and t[1] in keywords]
    alreadyConsidered = ignoreops + [t[0] for t in threadstoscrape] + scrapednosdic["doneops"]
    #Board Catalog JSON
    try:
        print("~Getting JSON for catalog of /{}/~".format(boardcode))
        catalogjson_url = ("https://a.4cdn.org/{}/catalog.json".format(boardcode))
        catalogjson_file = urllib.request.urlopen(catalogjson_url)
        catalogjson = json.load(catalogjson_file)
        #Search ops not considered already
        for page in catalogjson:
            for threadop in page["threads"]:
                if not threadop["no"] in alreadyConsidered:
                    boxbreak=0
                    boxestocheck=[b for b in boxestocheckfor["4chan"] if b in threadop]
                    for boxtocheck in boxestocheck:
                        for keyword in keywords:
                            if keyword in threadop[boxtocheck].lower():
                                threadstoscrape.append([threadop["no"],keyword,[]])
                                boxbreak=1
                                break
                        if boxbreak==1:
                            break
    except:
        print("Error: Cannot load catalog for /{}/".format(boardcode))

    scrapednosdic_return = {"doneops":scrapednosdic["doneops"], "active":[]}
    if threadstoscrape:
        #Compute padding for progress bar placement:
        maxsize = max([len(str(t[0]))+len(t[1]) for t in threadstoscrape])
        threadstoscrape_padded = [t+[maxsize-(len(str(t[0]))+len(t[1]))] for t in threadstoscrape]
        #Actually do the scraping now
        for ttsp in threadstoscrape_padded:
            result = scrapethread(boardcode,*ttsp)
            if result[0] == 'keep':
                scrapednosdic_return["active"].append([ttsp[0],ttsp[1],result[1]])
            else:
                scrapednosdic_return["doneops"].insert(0,ttsp[0])

    return scrapednosdic_return

################################################################################

def scrapethread(boardcode,threadopno,keyword,scrapednos,padding):
    global lock
    filelist = getfilelist(boardcode,threadopno,keyword,'4chan')
    filestart = 0
    if filelist[0] in ['try_4plebs']:
        filelist = getfilelist(boardcode,threadopno,keyword,'4plebs')
        filestart = 1
    if filelist[0] in ['keep','delete']:
        return [filelist[0],scrapednos]
    #otherwise 'success'
    impostslist = filelist[1]

    #Try to create folder
    threadaddress=("{}\\{} {}".format(boardcode,str(threadopno),keyword))
    try:
        os.makedirs(threadaddress,exist_ok=True)
    except:
        print("Error: failed to create folder '{}'".format(threadaddress))
        return ['keep',scrapednos]

    #Scrape files
    progressmsg.progmsg(msg="Scraping /{}/:{}:{} {}".format(boardcode,str(threadopno),keyword,' '*padding),of=len(impostslist))
    keepflag = 0

    postbuffers = [[] for i in range(num_download_threads)]
    def scrapefile_download_thread(dtid):
        nonlocal keepflag, postbuffers
        while True:
            with lock:
                try:
                    postbuffers[dtid] = impostslist.pop(0)
                    if int(postbuffers[dtid]["no"]) in scrapednos:
                        progressmsg.tick()
                        continue
                except:
                    return
            for modus in ['4chan','4plebs','4plebsthumbs'][filestart:]:
                if modus == '4plebsthumbs':
                    with lock:
                        try:
                            os.makedirs('{}\\thumbs'.format(threadaddress),exist_ok=True)
                        except:
                            progressmsg.progmsg(msg="Error: failed to create folder \'{}\\thumbs\' ".format(threadaddress))
                            keepflag = 1
                            break
                result = scrapefile(threadaddress,postbuffers[dtid],modus,boardcode,threadopno,keyword)
                with lock:
                    if result == 'success':
                        scrapednos.append(int(postbuffers[dtid]["no"]))
                        progressmsg.tick()
                        break
                    elif result == 'keep':
                        keepflag = 1
                        break
                    elif result == 'try_next_modus':
                        continue

    download_threads = [threading.Thread(target=scrapefile_download_thread,args=[i]) for i in range(num_download_threads)]
    for t in download_threads:
        t.start()
    for t in download_threads:
        t.join()
    progressmsg.finish()

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

def getfilelist(boardcode,threadopno,keyword,modus):
    global plebboards,plebsHTTPHeader

    if modus == '4chan':
        try:
            threadjson_url = 'https://a.4cdn.org/{}/thread/{}.json'.format(boardcode,str(threadopno))
            threadjson_file = urllib.request.urlopen(threadjson_url)
            threadjson = json.load(threadjson_file)
            impostslist = [{"no":post['no'],"tim":post['tim'],"ext":post['ext']} for post in threadjson["posts"] if "tim" in post]
            return ['now_scrape',impostslist,'archived' in threadjson["posts"][0]]
        except Exception as e:
            #Thread error:
            if hasattr(e,'code') and e.code == 404: # pylint: disable=E1101
                if boardcode in plebboards:
                    #If 404 error and plebboard then try to get thread JSON from 4plebs
                    print("Thread /{}/:{}:{} not found on 4chan, trying 4plebs".format(boardcode,str(threadopno),keyword))
                    return ['try_4plebs']
                else:
                    print("Thread /{}/:{}:{} not found on 4chan and not on 4plebs".format(boardcode,str(threadopno),keyword))
                    return ['delete']
            else:
                print("Error: Cannot load 4chan thread /{}/:{}:{}".format(boardcode,str(threadopno),keyword))
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
                impostslist.append({"no":threadjson[str(threadopno)]["op"]["num"],"tim":os.path.splitext(threadjson[str(threadopno)]["op"]["media"]["media"])[0],"ext":os.path.splitext(threadjson[str(threadopno)]["op"]["media"]["media"])[1]})
            if "posts" in threadjson[str(threadopno)]:
                for postvalue in threadjson[str(threadopno)]["posts"].values():
                    if postvalue["media"] != None:
                        impostslist.append({"no":str(postvalue["num"]),"tim":os.path.splitext(postvalue["media"]["media"])[0],"ext":os.path.splitext(postvalue["media"]["media"])[1]})
            return ['now_scrape',impostslist]
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']: # pylint: disable=E1101
                print("Thread /{}/:{}:{} not found on 4plebs".format(boardcode,str(threadopno),keyword))
                return ['delete']
            else:
                print("Error: Cannot load 4plebs thread /{}/:{}:{}".format(boardcode,str(threadopno),keyword))
                return ['keep']

################################################################################

def scrapefile(threadaddress,post,modus,boardcode,threadopno,keyword):
    global plebboards

    if modus == '4chan':
        try:
            imgaddress = "{}\\{}{}".format(threadaddress,str(post["no"]),post["ext"])
            if os.path.exists(imgaddress):
                with lock:
                    progressmsg.progmsg(msg="Error: File /{}/:{}:{}:{} already exists; please move it ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'
            imgdomain = 'https://i.4cdn.org/'
            imgurl = "{}{}/{}{}".format(imgdomain,boardcode,str(post["tim"]),post["ext"])
            urllib.request.urlretrieve(imgurl,imgaddress)
            return 'success'
        except Exception as e:
            if hasattr(e,'code') and e.code == 404: # pylint: disable=E1101
                if boardcode in plebboards:
                    with lock:
                        progressmsg.progmsg(msg="File /{}/:{}:{}:{} not found on 4chan, scraping 4plebs file ".format(boardcode,threadopno,keyword,str(post["no"])))
                    return 'try_next_modus'
                else:
                    with lock:
                        progressmsg.progmsg(msg="File /{}/:{}:{}:{} not found on 4chan and not on 4plebs ".format(boardcode,threadopno,keyword,str(post["no"])))
                    return 'success'
            else:
                with lock:
                    progressmsg.progmsg(msg="Error: Cannot load 4chan file /{}/:{}:{}:{} ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'

    elif modus == '4plebs':
        try:
            imgaddress = "{}\\{}{}".format(threadaddress,str(post["no"]),post["ext"])
            if os.path.exists(imgaddress):
                with lock:
                    progressmsg.progmsg(msg="Error: File /{}/:{}:{}:{} already exists; please move it ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'
            imgdomain = 'https://i.4pcdn.org/'
            imgurl = "{}{}/{}{}".format(imgdomain,boardcode,str(post["tim"]),post["ext"])
            urllib.request.urlretrieve(imgurl,imgaddress)
            return 'success'
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']: # pylint: disable=E1101
                with lock:
                    progressmsg.progmsg(msg="File /{}/:{}:{}:{} not found on 4plebs, scraping 4plebs thumbnail ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'try_next_modus'
            else:
                with lock:
                    progressmsg.progmsg(msg="Error: Cannot load 4plebs file /{}/:{}:{}:{} ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'

    elif modus == '4plebsthumbs':
        try:
            threadaddress = '{}\\thumbs'.format(threadaddress)
            imgaddress = "{}\\{}.jpg".format(threadaddress,str(post["no"]))
            if os.path.exists(imgaddress):
                with lock:
                    progressmsg.progmsg(msg="Error: File /{}/:{}:{}:{}(thumb) already exists; please move it ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'
            imgdomain = 'https://i.4pcdn.org/'
            imgurl = "{}{}/{}s.jpg".format(imgdomain,boardcode,str(post["tim"]))
            urllib.request.urlretrieve(imgurl,imgaddress)
            return 'success'
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']: # pylint: disable=E1101
                with lock:
                    progressmsg.progmsg(msg="File /{}/:{}:{}:{}(thumb) not found on 4plebs ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'success'
            else:
                with lock:
                    progressmsg.progmsg(msg="Error: Cannot load 4plebs file /{}/:{}:{}:{}(thumb) ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'

################################################################################

def viewscraping():
    nonemptyBoards_keywords = [b for b in configjson["boards"] if configjson["boards"][b]["keywords"]]
    if not nonemptyBoards_keywords:
        print("Currently not scraping any boards")
        return False
    else:
        print("Currently scraping:")
        for board in nonemptyBoards_keywords:
            print("/{}/: ".format(board),end="")
            for keyword in configjson["boards"][board]["keywords"][:-1]:
                print(keyword,end=", ")
            print(configjson["boards"][board]["keywords"][-1])

################################################################################

def viewrequests():
    nonemptyBoards_requests = [b for b in configjson["boards"] if configjson["boards"][b]["requests"]]
    if not nonemptyBoards_requests:
        print("Currently no special requests")
    else:
        print("Current special requests:")
        for board in nonemptyBoards_requests:
            for req in configjson["boards"][board]["requests"]:
                print("/{}/:{}:{}".format(board,str(req[0]),req[1]))

################################################################################

def viewblacklisting():
    nonemptyBoards_blacklist = [b for b in configjson["boards"] if configjson["boards"][b]["blacklist"]]
    if not nonemptyBoards_blacklist:
        print("Currently not blacklisting any threads")
    else:
        print("Currently blacklisting:")
        for board in nonemptyBoards_blacklist:
            print("/{}/: ".format(board),end="")
            for opno in configjson["boards"][board]["blacklist"][:-1]:
                print(str(opno),end=", ")
            print(str(configjson["boards"][board]["blacklist"][-1]))

################################################################################

def plebrequest(boardcode,keyword):
    global boxestocheckfor,plebsHTTPHeader,configjson
    print("Searching 4plebs archive for threads on /{}/ containing \'{}\'".format(boardcode,keyword))
    opnos = []
    for boxtocheckfor in boxestocheckfor["4plebs"]:
        searchjson_url = 'http://archive.4plebs.org/_/api/chan/search/?type=op&boards={}&{}={}'.format(boardcode,boxtocheckfor,keyword.replace(" ","%20"))
        cooldown_loop = True
        while cooldown_loop:
            searchjson_file = urllib.request.urlopen(urllib.request.Request(searchjson_url,None,{'User-Agent':plebsHTTPHeader}))
            searchjson = json.load(searchjson_file)
            if "error" in searchjson:
                if searchjson["error"] == "No results found.":
                    cooldown_loop = False
                elif searchjson["error"].startswith("Search limit exceeded."):
                    sleeptime = 60 #sleeptime = 5 + int(searchjson["error"][35:37].strip()) #35 to 37 hardcoded for time
                    print("Sleeping for {} seconds (4plebs cooldown)".format(sleeptime))
                    sleep(sleeptime)
            else:
                for post in searchjson["0"]["posts"]:
                    opnos.append(int(post["num"]))
                cooldown_loop = False

    opnos = list(set(opnos).difference(set([req[0] for req in configjson["boards"][boardcode]["requests"]])))
    for opno in opnos:
        configjson["boards"][boardcode]["requests"].append([opno,keyword,[]])
    if opnos:
        opnos_len = len(opnos)
        print("Added {} special request{}".format(opnos_len,"" if opnos_len==1 else "s"))
    else:
        print("No more special requests added")

################################################################################

def saveconfig():
    with open('scraperconfig.json','w') as configjson_file:
        configjson_file.write(json.dumps(configjson))

################################################################################

class class_progressmsg():
    def __init__(self):
        self.resetvars()

    def resetvars(self):
        self.msg = ""
        self.pos = 0
        self.of = 1
        self.bsnum = 0
        self.active = False

    def progmsg(self,*args,**kwargs):
        if 'msg' in kwargs:
            self.msg = kwargs['msg']
        if 'pos' in kwargs:
            self.pos = int(kwargs['pos'])
        if 'of' in kwargs:
            self.of = kwargs['of']
        if self.active == True:
            stdout.write('\n')
            stdout.flush()
        stdout.write(self.msg)
        stdout.flush()
        self.printprog()
        self.active = True

    def printprog(self):
        hashund = ('#'*int(10*(self.pos/self.of))).ljust(10,'_')
        prog = '[{}] ({}/{})'.format(hashund,self.pos,self.of)
        self.bsnum = len(prog)
        stdout.write(prog)
        stdout.flush()

    def tick(self):
        if self.active:
            self.pos+=1
            stdout.write('\b'*self.bsnum)
            self.printprog()
            if self.pos == self.of:
                self.finish()

    def finish(self):
        if self.active:
            stdout.write('\n')
            stdout.flush()
        self.resetvars()

################################################################################

def update_scraper():
    def download_update(downloadVersion):
        try:
            fpath = os.path.realpath(__file__)
            latestVersionProgram_url = "https://raw.githubusercontent.com/SelfAdjointOperator/4chan-Scraper/{}/4chan%20Scraper.py".format(downloadVersion)
            urllib.request.urlretrieve(latestVersionProgram_url,fpath+".tmp")
            os.remove(fpath)
            os.rename(fpath+".tmp",fpath)
            return True
        except:
            return False

    try:
        print("Checking for updates...")
        latestVersionJson_url = "https://api.github.com/repos/selfadjointoperator/4chan-scraper/releases/latest"
        latestVersionJson_file = urllib.request.urlopen(latestVersionJson_url)
        latestVersionJson = json.load(latestVersionJson_file)
        webversionv = latestVersionJson["tag_name"]
        if webversionv[1:] == version: #versions always vX.Y.Z; remove v
            print("Latest version running")
        else:
            print("Downloading new version {}...".format(webversionv))
            if download_update(webversionv) is True:
                print("Restarting new version in 3",end="",flush=True)
                for i in range(3):
                    sleep(1)
                    print("\b{}".format(str(2-i)),end="",flush=True)
                os.startfile(os.path.realpath(__file__))
                raise SystemExit
            else:
                print("Error: Unable to download updates; running current version")
    except SystemExit:
        raise SystemExit
    except:
        print("Error: Unable to check for updates; running current version")

################################################################################

def printhelp():
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

################################################################################

#Main Thread Here

lock = threading.Lock()
progressmsg = class_progressmsg()

print('~~~~~~~~~~~~~~~~~~~~~~~')
print('BATEMAN\'S 4CHAN SCRAPER')
print('~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~Version {}~~~~~'.format(version))

#Check for updates
if auto_update is True:
    print()
    update_scraper()

#Load or create config JSON
if os.path.exists('scraperconfig.json'):
    with open('scraperconfig.json') as configjson_file:
        configjson = json.load(configjson_file)
else:
    configjson = new_config()
    saveconfig()
    print("\nCreated config file 'scraperconfig.json'")

#Main loop
while True:
    print('\n')
    action = input("What do you want to do? (SCRAPE/SCRAPEQUIT/REQUEST/PLEBREQUEST/BLACKLIST/VIEW/ADD/DELETE/HELP/QUIT) ").upper().strip()
    print('\n')

    if action in ["QUIT","Q"]:
        break

    elif action in ["HELP","H"]:
        printhelp()

    elif action in ["SCRAPE","S"]:
        scrape()

    elif action in ["SCRAPEQUIT","SQ"]:
        scrape()
        break

    elif action in ["REQUEST","R"]:
        viewrequests()
        board = input("\nWhich board is the thread on? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        try:
            requestopno = int(input("What is the OP number of the requested thread? ").strip())
        except:
            print("Error: Invalid number")
            continue
        possible_new_board(board)
        alreadyreq = [req for req in configjson["boards"][board]["requests"] if req[0] == requestopno]
        if alreadyreq:
            for req in alreadyreq:
                configjson["boards"][board]["requests"].remove(req)
                print("Thread /{}/:{}:{} removed from special requests".format(board,str(req[0]),req[1]))
        else:
            keyword = input("What keyword(s) to tag folder with? ").lower().replace("_"," ").strip()
            if not keyword:
                keyword = "request"
            configjson["boards"][board]["requests"].append([requestopno,keyword,[]])
            print("Thread /{}/:{}:{} added to special requests".format(board,str(requestopno),keyword))
        saveconfig()

    elif action in ["PLEBREQUEST","P","PR"]:
        viewrequests()
        plebrequest_board = input("\nWhat board to search on? ").lower().strip()
        if not plebrequest_board:
            print("No board supplied")
            continue
        plebrequest_keyword = input("What keyword to search 4plebs for? ").lower().replace("_"," ").strip()
        if not plebrequest_keyword:
            print("No keyword supplied")
            continue
        possible_new_board(plebrequest_board)
        plebrequest(plebrequest_board,plebrequest_keyword)
        saveconfig()

    elif action in ["BLACKLIST","B","BLACK","BL"]:
        viewblacklisting()
        board = input("\nWhich board is the thread on? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        try:
            blacklistopno = int(input("What is the OP number of the thread to blacklist? ").strip())
        except:
            print("Error: Invalid number")
            continue
        possible_new_board(board)
        if blacklistopno in configjson["boards"][board]["blacklist"]:
            configjson["boards"][board]["blacklist"].remove(blacklistopno)
            print("No longer blacklisting /{}/:{}".format(board,str(blacklistopno)))
        else:
            configjson["boards"][board]["blacklist"].append(blacklistopno)
            print("Now blacklisting /{}/:{}".format(board,str(blacklistopno)))
        saveconfig()

    elif action in ["VIEW","V"]:
        viewrequests()
        print()
        viewscraping()
        print()
        viewblacklisting()

    elif action in ["ADD","A"]:
        viewscraping()
        board = input("\nWhich board to add keywords to? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        keywordstoadd = input("Which keywords to start scraping for? ").lower().split()
        keywordstoadd = [keyword.replace("_"," ").strip() for keyword in keywordstoadd if keyword.replace("_"," ").strip() != ""]
        possible_new_board(board)
        addedcounter = 0
        for keyword in keywordstoadd:
            if not keyword in configjson["boards"][board]["keywords"]:
                configjson["boards"][board]["keywords"].append(keyword)
                addedcounter += 1
        configjson["boards"][board]["keywords"] = sorted(configjson["boards"][board]["keywords"])
        if addedcounter == 0:
            if not configjson["boards"][board]["keywords"]:
                print("No keywords added for /{}/, not scraping it".format(board))
            else:
                print("No more keywords added for /{}/".format(board))
        else:
            print("Keywords for /{}/ updated to: ".format(board),end="")
            for keyword in configjson["boards"][board]["keywords"][:-1]:
                print(keyword,end=", ")
            print(configjson["boards"][board]["keywords"][-1])
        saveconfig()

    elif action in ["DELETE","DEL","D"]:
        if viewscraping() is False:
            continue
        board = input("\nWhich board to delete keywords from? ").lower().strip()
        if not board:
            print("No board supplied")
            continue
        if not board in configjson["boards"] or not configjson["boards"][board]:
            print("Currently not scraping /{}/".format(board))
            continue
        keywordstodel = input("Which keywords to stop scraping for? ").lower().split()
        keywordstodel = [keyword.replace("_"," ").strip() for keyword in keywordstodel if keyword.replace("_"," ").strip() != ""]
        delcounter = 0
        for keyword in keywordstodel:
            if keyword in configjson["boards"][board]["keywords"]:
                configjson["boards"][board]["keywords"].remove(keyword)
                delcounter += 1
        if delcounter == 0:
            print("No keywords removed for /{}/".format(board))
        elif not configjson["boards"][board]["keywords"]:
            print("Stopped scraping /{}/".format(board))
        else:
            print("Keywords for /{}/ updated to: ".format(board),end="")
            for keyword in configjson["boards"][board]["keywords"][:-1]:
                print(keyword,end=", ")
            print(configjson["boards"][board]["keywords"][-1])
        saveconfig()

    else:
        print("Unknown command")

################################################################################


