##################################
#####BATEMAN'S 4CHAN SCRAPER######
##################################
##github.com/SelfAdjointOperator##
##################################

import urllib.request   #   getting files from web
import json             #   config file json to and from dictionary
import os               #   creating folders
import threading        #   multiple simultaneous downloads
from sys import stdout  #   for progress bar
from time import sleep  #   sleep if 4plebs search cooldown reached

version = '1.5.1'
newconfigjson = {"keywords": {}, "lastscrapeops": {}, "specialrequests": [], "blacklistedopnos": {}, "scrapednos": {}}
boxestocheckfor = {"4chan":["name","sub","com","filename"],"4plebs":["username","subject","text","filename"]}
no4chanArchiveBoards = ["b","bant","f","trash"] # unused, probably not implementing ifelse ifelse ifelse to save a couple of 404s
plebboards = ['adv','f','hr','o','pol','s4s','sp','tg','trv','tv','x']
glowiebypass = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
num_download_threads = 4

################################################################################

def scrape():
    if not configjson["specialrequests"]:
        print("Currently no special requests")
    else:
        print("~Doing special requests~")
        maxsize = max([len(srq[0])+len(str(srq[1]))+len(srq[2]) for srq in configjson["specialrequests"]])
        srqwithpad = [[srq[0],srq[1],srq[2],maxsize-(len(srq[0])+len(str(srq[1]))+len(srq[2]))] for srq in configjson["specialrequests"]]
        configjson["specialrequests"] = [srqp[:-1] for srqp in srqwithpad if scrapethread(*srqp)=='keep']
    print()
    if not configjson["keywords"]:
        print("Currently not scraping any boards\n")
    else:
        reqignorelist = [srq[1] for srq in configjson["specialrequests"]]
        for boardcode in configjson["keywords"]:
            configjson["lastscrapeops"][boardcode]=scrapeboard(boardcode,configjson["keywords"][boardcode],configjson["lastscrapeops"][boardcode],configjson["blacklistedopnos"][boardcode]+reqignorelist)
            print()
    maintenance()
    print("~Updating config~")
    saveconfig()
    print("~Config updated~")
    print("~Done scraping~")

################################################################################

def scrapeboard(boardcode,keywords,lastscrapeops,ignorelist):
    global boxestocheckfor
    threadstoscrape = [lsop for lsop in lastscrapeops if not lsop[0] in ignorelist and lsop[1] in keywords]
    #Board Catalog JSON
    try:
        print("~Getting JSON for catalog of /{}/~".format(boardcode))
        catalogjson_url = ("https://a.4cdn.org/{}/catalog.json".format(boardcode))
        catalogjson_file = urllib.request.urlopen(catalogjson_url)
        catalogjson = json.load(catalogjson_file)
        threadsgathered = []
        #Search each thread for keywords and append to list for scraping
        for page in catalogjson:
            for threadop in page["threads"]:
                if not threadop["no"] in ignorelist:
                    boxbreak=0
                    boxestocheck=[b for b in boxestocheckfor["4chan"] if b in threadop]
                    for boxtocheck in boxestocheck:
                        for keyword in keywords:
                            if keyword in threadop[boxtocheck].lower():
                                threadsgathered.append([threadop["no"],keyword])
                                boxbreak=1
                                break
                        if boxbreak==1:
                            break
        threadstoscrape += [tg for tg in threadsgathered if not tg[0] in [tts[0] for tts in threadstoscrape]]
    except:
        print("Error: Cannot load catalog for /{}/".format(boardcode))

    scrapedactiveops = []
    if threadstoscrape:
        #Compute padding for progress bar placement:
        maxsize = max([len(str(tts[0]))+len(tts[1]) for tts in threadstoscrape])
        ttswithpad = [[tts[0],tts[1],maxsize-(len(str(tts[0]))+len(tts[1]))] for tts in threadstoscrape]
        #Actually do the scraping now
        for ttst in ttswithpad:
            if scrapethread(boardcode,*ttst) == 'keep':
                scrapedactiveops.append(ttst[:-1])

    return scrapedactiveops

################################################################################

def scrapethread(boardcode,threadopno,keyword,padding):
    global lock
    filelist = getfilelist(boardcode,threadopno,keyword,'4chan')
    filestart = 0
    if filelist[0] in ['try_4plebs']:
        filelist = getfilelist(boardcode,threadopno,keyword,'4plebs')
        filestart = 1
    if filelist[0] in ['keep','delete']:
        return filelist[0]
    impostslist = filelist[1]

    #Try to create folder
    threadaddress=("{}\\{} {}".format(boardcode,str(threadopno),keyword))
    try:
        os.makedirs(threadaddress,exist_ok=True)
    except:
        print("Error: failed to create folder '{}'".format(threadaddress))
        return 'keep'

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
                    if int(postbuffers[dtid]["no"]) in configjson["scrapednos"][boardcode]:
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
                        configjson["scrapednos"][boardcode].insert(0,int(postbuffers[dtid]["no"]))
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
        return 'delete'
    else:
        return 'keep'

################################################################################

def getfilelist(boardcode,threadopno,keyword,modus):
    global plebboards,glowiebypass

    if modus == '4chan':
        try:
            threadjson_url = 'https://a.4cdn.org/{}/thread/{}.json'.format(boardcode,str(threadopno))
            threadjson_file = urllib.request.urlopen(threadjson_url)
            threadjson = json.load(threadjson_file)
            impostslist = [{"no":post['no'],"tim":post['tim'],"ext":post['ext']} for post in threadjson["posts"] if "tim" in post]
            return ['success',impostslist,'archived' in threadjson["posts"][0]]
        except Exception as e:
            #Thread error:
            if hasattr(e,'code') and e.code == 404:
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
            threadjson_file = urllib.request.urlopen(urllib.request.Request(threadjson_url,None,{'User-Agent':glowiebypass}))
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
            return ['success',impostslist]
        except Exception as e:
            if hasattr(e,'code') and e.code in [404,'404']:
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
            if hasattr(e,'code') and e.code == 404:
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
            if hasattr(e,'code') and e.code in [404,'404']:
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
            if hasattr(e,'code') and e.code in [404,'404']:
                with lock:
                    progressmsg.progmsg(msg="File /{}/:{}:{}:{}(thumb) not found on 4plebs ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'success'
            else:
                with lock:
                    progressmsg.progmsg(msg="Error: Cannot load 4plebs file /{}/:{}:{}:{}(thumb) ".format(boardcode,threadopno,keyword,str(post["no"])))
                return 'keep'

################################################################################

def viewscraping():
    if not configjson["keywords"]:
        print("Currently not scraping any boards")
    else:
        print("Currently scraping:")
        for board in configjson["keywords"]:
            print("/{}/:".format(board),end=" ")
            for keyword in configjson["keywords"][board][:-1]:
                print("'{}',".format(keyword),end=" ")
            print("\'{}\'".format(configjson["keywords"][board][-1]))

################################################################################

def viewrequests():
    if not configjson["specialrequests"]:
        print("Currently no special requests")
    else:
        print("Current special requests:")
        for req in configjson["specialrequests"]:
            print("/{}/:{}:{}".format(req[0],str(req[1]),req[2]))

################################################################################

def viewblacklisting():
    nonemptyblbs = [blb for blb in configjson["blacklistedopnos"] if configjson["blacklistedopnos"][blb]]
    if not nonemptyblbs:
        print("Currently not blacklisting any threads")
    else:
        print("Currently blacklisting:")
        for blb in nonemptyblbs:
            print("/{}/:".format(blb),end=" ")
            for opno in configjson["blacklistedopnos"][blb][:-1]:
                print(str(opno),end=", ")
            print(str(configjson["blacklistedopnos"][blb][-1]))

################################################################################

def plebrequest(boardcode,keyword):
    global boxestocheckfor,glowiebypass,configjson
    print("Searching 4plebs archive for threads on /{}/ containing \'{}\'".format(boardcode,keyword))
    opnos = []
    for search_option in boxestocheckfor["4plebs"]:
        searchjson_url = 'http://archive.4plebs.org/_/api/chan/search/?type=op&boards={}&{}={}'.format(boardcode,search_option,keyword.replace(" ","%20"))
        cooldown_loop = True
        while cooldown_loop:
            searchjson_file = urllib.request.urlopen(urllib.request.Request(searchjson_url,None,{'User-Agent':glowiebypass}))
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

    opnos = list(set(opnos).difference(set([req[1] for req in configjson["specialrequests"]])))
    for opno in opnos:
        configjson["specialrequests"].append([boardcode,opno,keyword])
    if opnos:
        print("Added {} special requests".format(len(opnos)))
    else:
        print("No more special requests added")

################################################################################

def maintenance():
    print("~Performing maintenance~")
    for board in configjson['keywords']:
        configjson['keywords'][board] = sorted(configjson['keywords'][board])
    for board in configjson['blacklistedopnos']:
        configjson['blacklistedopnos'][board] = sorted(list(set(configjson['blacklistedopnos'][board])),reverse=True)
    for board in configjson['scrapednos']:
        configjson['scrapednos'][board] = sorted(list(set(configjson['scrapednos'][board])),reverse=True)
    for board in configjson['lastscrapeops']:
        lastscrapeops_set = set(map(tuple,configjson['lastscrapeops'][board]))
        lastscrapeops_gen = map(list,lastscrapeops_set)
        configjson['lastscrapeops'][board] = [x for x in lastscrapeops_gen]
    print("~Maintenance complete~")

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
        self.printmsg()
        self.printprog()
        self.active = True
        if 'tick' in kwargs:
            self.tick()

    def printmsg(self):
        stdout.write(self.msg)
        stdout.flush()

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

#Main Thread Here

lock = threading.Lock()
progressmsg = class_progressmsg()

print('~~~~~~~~~~~~~~~~~~~~~~~')
print('BATEMAN\'S 4CHAN SCRAPER')
print('~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~Version {}~~~~~'.format(version))

#Load or create config JSON
if os.path.exists('scraperconfig.json'):
    with open('scraperconfig.json') as configjson_file:
        configjson = json.load(configjson_file)
else:
    configjson = newconfigjson
    saveconfig()
    print("\nCreated config file 'scraperconfig.json'")

#Main loop
while True:
    print('\n')
    action = input("What do you want to do? (SCRAPE/SCRAPEQUIT/REQUEST/PLEBREQUEST/BLACKLIST/VIEW/ADD/DELETE/MAINTENANCE/HELP/QUIT) ").upper().strip()
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
        print("MAINTENANCE /  M: Remove any possible duplicate numbers that have arisen in the config from external editing and reorder in descending order for faster search time. Keywords are also put into alphabetical order")
        print("HELP        /  H: Shows this help text")
        print("QUIT        /  Q: Closes the program")

    elif action in ["SCRAPE","S"]:
        scrape()

    elif action in ["SCRAPEQUIT","SQ"]:
        scrape()
        break

    elif action in ["REQUEST","R"]:
        viewrequests()
        requestboard = input("\nWhich board is the thread on? ").lower().strip()
        if not requestboard:
            print("No board supplied")
            continue
        try:
            requestopno = int(input("What is the OP number of the requested thread? ").strip())
        except:
            print("Error: Invalid number")
            continue
        alreadyreq = [req for req in configjson['specialrequests'] if [req[0],req[1]] == [requestboard,requestopno]]
        if alreadyreq:
            for req in alreadyreq:
                configjson["specialrequests"].remove(req)
                print("Thread /{}/:{}:{} removed from special requests".format(req[0],str(req[1]),req[2]))
        else:
            requestkeyword = input("What keyword(s) to tag folder with? ").lower().replace("_"," ").strip()
            if not requestkeyword:
                requestkeyword = "request"
            if not requestboard in configjson["scrapednos"]:
                configjson["scrapednos"][requestboard]=[]
            if not [requestboard,requestopno,requestkeyword] in configjson["specialrequests"]:
                configjson["specialrequests"].append([requestboard,requestopno,requestkeyword])
                print("Thread /{}/:{}:{} added to special requests".format(requestboard,str(requestopno),requestkeyword))
        saveconfig()

    elif action in ["PLEBREQUEST","P","PR"]:
        #put in reminder of 1 min cooldown
        plebrequest_board = input("What board to search on? ").lower().strip()
        if not plebrequest_board:
            print("No board supplied")
            continue
        plebrequest_keyword = input("What keyword to search 4plebs for? ").lower().replace("_"," ").strip()
        if not plebrequest_keyword:
            print("No keyword supplied")
            continue
        plebrequest(plebrequest_board,plebrequest_keyword)
        saveconfig()

    elif action in ["BLACKLIST","B","BLACK","BL"]:
        viewblacklisting()
        blacklistboard = input("\nWhich board is the thread on? ").lower().strip()
        if not blacklistboard:
            print("No board supplied")
            continue
        try:
            blacklistopno = int(input("What is the OP number of the thread to blacklist? ").strip())
        except:
            print("Error: Invalid number")
            continue
        if not blacklistboard in configjson["blacklistedopnos"]:
            configjson["blacklistedopnos"][blacklistboard]=[]
        if not blacklistopno in configjson["blacklistedopnos"][blacklistboard]:
            configjson["blacklistedopnos"][blacklistboard].append(blacklistopno)
            print("Now blacklisting /{}/:{}".format(blacklistboard,str(blacklistopno)))
        else:
            configjson["blacklistedopnos"][blacklistboard].remove(blacklistopno)
            print("No longer blacklisting /{}/:{}".format(blacklistboard,str(blacklistopno)))
        saveconfig()

    elif action in ["VIEW","V"]:
        viewrequests()
        print()
        viewscraping()
        print()
        viewblacklisting()

    elif action in ["ADD","A"]:
        viewscraping()
        boardtomodify = input("\nWhich board to add keywords to? ").lower().strip()
        if not boardtomodify:
            print("No board supplied")
            continue
        keywordstoadd = input("Which keywords to start scraping for? ").lower().split()
        keywordstoadd = [keyword.replace("_"," ").strip() for keyword in keywordstoadd if keyword.replace("_"," ").strip() != ""]
        if not keywordstoadd:
            if boardtomodify in configjson["keywords"]:
                print("No more keywords added for /{}/".format(boardtomodify))
            else:
                print("No keywords added for /{}/, not scraping it".format(boardtomodify))
            continue
        if not boardtomodify in configjson["keywords"]:
            configjson["keywords"][boardtomodify]=[]
        if not boardtomodify in configjson["lastscrapeops"]:
            configjson["lastscrapeops"][boardtomodify]=[]
        if not boardtomodify in configjson["blacklistedopnos"]:
            configjson["blacklistedopnos"][boardtomodify]=[]
        if not boardtomodify in configjson["scrapednos"]:
            configjson["scrapednos"][boardtomodify]=[]
        for keyword in keywordstoadd:
            if not keyword in configjson["keywords"][boardtomodify]:
                configjson["keywords"][boardtomodify].append(keyword)
        print("Keywords for /{}/ updated to:".format(boardtomodify),end=" ")
        for keyword in configjson["keywords"][boardtomodify][:-1]:
            print("'{}',".format(keyword),end=" ")
        print("'{}'".format(configjson["keywords"][boardtomodify][-1]))
        saveconfig()

    elif action in ["DELETE","DEL","D"]:
        if not configjson["keywords"]:
            print("Currently not scraping any boards")
            continue
        viewscraping()
        boardtomodify = input("\nWhich board to delete keywords from? ").lower().strip()
        if not boardtomodify:
            print("No board supplied")
            continue
        if not boardtomodify in configjson["keywords"]:
            print("Currently not scraping /{}/".format(boardtomodify))
            continue
        keywordstodel = input("Which keywords to stop scraping for? ").lower().split()
        keywordstodel = [keyword.replace("_"," ").strip() for keyword in keywordstodel if keyword.replace("_"," ").strip() != ""]
        if not keywordstodel:
            print("No keywords removed for /{}/".format(boardtomodify))
            continue
        for keyword in keywordstodel:
            if keyword in configjson["keywords"][boardtomodify]:
                configjson["keywords"][boardtomodify].remove(keyword)
        if not configjson["keywords"][boardtomodify]:
            print("Stopped scraping /{}/".format(boardtomodify))
            del configjson["keywords"][boardtomodify]
        else:
            print("Keywords for /{}/ updated to:".format(boardtomodify),end=" ")
            for keyword in configjson["keywords"][boardtomodify][:-1]:
                print("'{}',".format(keyword),end=" ")
            print("'{}'".format(configjson["keywords"][boardtomodify][-1]))
        saveconfig()

    elif action in ["MAINTENANCE","M"]:
        maintenance()
        saveconfig()

    else:
        print("Unknown command")

################################################################################

