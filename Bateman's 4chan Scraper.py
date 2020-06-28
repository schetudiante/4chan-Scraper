from io import BytesIO
import urllib.request
import json
import os

################################################################################

def scrape():
    if not configjson["specialrequests"]:
        print("Currently no special requests")
        print('\n')
    else:
        print("~Doing special requests~")
        configjson["specialrequests"]=[req for req in configjson["specialrequests"] if scrapethread(req[0],req[1],req[2])=="keep"]
        print('\n')
    if not configjson["keywords"]:
        print("Currently not scraping any boards")
    else:
        for boardcode in configjson["keywords"]:
            configjson["lastscrapeops"][boardcode]=scrapeboard(boardcode,configjson["keywords"][boardcode],boardcode in configjson["noarchiveboards"],configjson["lastscrapeops"][boardcode],configjson["blacklistedopnos"][boardcode])
            print('\n')
    print("~Updating log~")
    saveconfig()
    print("~Log updated~")
    print("~Done scraping~")

################################################################################

def scrapeboard(boardcode,keywords,noarchive,lastscrapeops,blacklist):
    boxestocheckfor=["name","sub","com","filename"]
    scrapedactiveops=[]
    #Board Catalog JSON
    try:
        print("~Getting JSON for catalog of /"+boardcode+"/~")
        catalogjson_url = ("https://a.4cdn.org/"+boardcode+"/catalog.json")
        catalogjson_file = urllib.request.urlopen(catalogjson_url)
        catalogjson = json.load(catalogjson_file)
        #Search each thread for keywords
        for page in catalogjson:
            for threadop in page["threads"]:
                if not threadop["no"] in blacklist:
                    boxbreak=0
                    boxestocheck=[b for b in boxestocheckfor if b in threadop]
                    for boxtocheck in boxestocheck:
                        for keyword in keywords:
                            if keyword in threadop[boxtocheck].lower():
                                if scrapethread(boardcode,threadop["no"],keyword) == "keep":
                                    scrapedactiveops.append([threadop["no"],keyword])
                                boxbreak=1
                                break
                        if boxbreak==1:
                            break
    except:
        print("Error: Cannot load catalog for /"+boardcode+"/")

    #Previously scraped and now archived threads
    if noarchive == False:
        possiblyarchivedlist = [lastscrapeop for lastscrapeop in lastscrapeops if not lastscrapeop[0] in [scrapedactiveop[0] for scrapedactiveop in scrapedactiveops] and not lastscrapeop[0] in blacklist and lastscrapeop[1] in keywords]
        if possiblyarchivedlist:
            for possiblyarchivedop in possiblyarchivedlist:
                if scrapethread(boardcode,possiblyarchivedop[0],possiblyarchivedop[1]) == "keep":
                    scrapedactiveops.append(possiblyarchivedop)

    return scrapedactiveops

################################################################################

def scrapethread(boardcode,threadopno,keyword):
    noerrs = 1
    #Try to create folder
    threadaddress=(boardcode+"\\"+str(threadopno)+" "+keyword)
    os.makedirs(threadaddress,exist_ok=True)
    if not os.path.exists(threadaddress):
        print("Error: failed to create folder '"+threadaddress+"'")
        return "keep"
    #Try to get thread JSON if not 404ed
    try:
        threadjson_url = ("https://a.4cdn.org/"+boardcode+"/thread/"+str(threadopno)+".json")
        threadjson_file = urllib.request.urlopen(threadjson_url)
        threadjson = json.load(threadjson_file)
        print("Scraping from /"+boardcode+"/:"+str(threadopno)+":"+keyword)
        for post in threadjson["posts"]:
            #If attachment present in JSON try to save from website if not 404ed
            if "tim" in post:
                if not post["no"] in configjson["scrapednos"][boardcode]:
                    imgurl=("https://i.4cdn.org/"+boardcode+"/"+str(post["tim"])+post["ext"])
                    imgaddress=(threadaddress+"\\"+str(post["no"])+post["ext"])
                    if not os.path.exists(imgaddress):
                        try:
                            urllib.request.urlretrieve(imgurl,imgaddress)
                            configjson["scrapednos"][boardcode].append(post["no"])
                        except Exception as e:
                            try:
                                if e.code == 404:
                                    configjson["scrapednos"][boardcode].append(post["no"])
                                    print("File /"+boardcode+"/:"+str(post["no"])+":"+keyword+" has expired")
                                else:
                                    raise Exception
                            except:
                                noerrs = 0
                                print("Error: could not load file /"+boardcode+"/:"+str(post["no"])+":"+keyword)
                    else:
                        noerrs = 0
                        print("Error: File /"+boardcode+"/:"+str(post["no"])+":"+keyword+" already exists; please move it")
        delfolderifempty(threadaddress)
        if noerrs == 1 and "archived" in threadjson["posts"][0]:
            return "delete"
        else:
            return "keep"
    except Exception as e:
        delfolderifempty(threadaddress)
        try:
            if e.code == 404:
                print("Thread /"+boardcode+"/:"+str(threadopno)+":"+keyword+" has expired")
                return "delete"
            else:
                raise Exception
        except:
            print("Error: Cannot load thread /"+boardcode+"/:"+str(threadopno)+":"+keyword)
            return "keep"

################################################################################

def delfolderifempty(address):
    if not [f for f in os.listdir(address) if f != "desktop.ini"]:
        try:
            os.rmdir(address)
        except:
            print("Error: Could not delete folder '"+address+"'")

################################################################################

def viewscraping():
    if not configjson["keywords"]:
        print("Currently not scraping any boards")
    else:
        print("Currently scraping:")
        for board in configjson["keywords"]:
            print("/"+board+"/:",end=" ")
            for keyword in configjson["keywords"][board][:-1]:
                print("'"+keyword,end="', ")
            print("'"+configjson["keywords"][board][-1]+"'")

################################################################################

def viewrequests():
    if configjson["specialrequests"]:
        print("Currently no special requests")
    else:
        print("Current special requests:")
        for req in configjson["specialrequests"]:
            print("/"+req[0]+"/:"+str(req[1])+":"+req[2])

################################################################################

def viewblacklisting():
    nonemptyblbs = [blb for blb in configjson["blacklistedopnos"] if configjson["blacklistedopnos"][blb]]
    if not nonemptyblbs:
        print("Currently not blacklisting any threads")
    else:
        print("Currently blacklisting:")
        for blb in nonemptyblbs:
            print("/"+blb+"/:",end=" ")
            for opno in configjson["blacklistedopnos"][blb][:-1]:
                print(str(opno),end=", ")
            print(str(configjson["blacklistedopnos"][blb][-1]))

################################################################################

def saveconfig():
    with open('scraperconfig.txt','w') as configjson_file:
        configjson_file.write(json.dumps(configjson))

################################################################################

#Main part of the program

print('~~~~~~~~~~~~~~~~~~~~~~~')
print('BATEMAN\'S 4CHAN SCRAPER')
print('~~~~~~~~~~~~~~~~~~~~~~~')
print('~~~~~Version 1.0.7~~~~~')

#Load or create config JSON
if os.path.exists('scraperconfig.txt'):
    with open('scraperconfig.txt') as configjson_file:
        configjson = json.load(configjson_file)
else:
    configjson = {"keywords": {}, "noarchiveboards": [], "lastscrapeops": {}, "specialrequests": [], "blacklistedopnos": {}, "scrapednos": {}}
    saveconfig()
    print("")
    print("Created config file 'scraperconfig.txt'")

#Main loop
while True:
    print('\n')
    action=input("What do you want to do? (SCRAPE/SCRAPEQUIT/REQUEST/BLACKLIST/VIEW/ADD/DELETE/HELP/QUIT) ").upper().strip()
    print('\n')

    if action in ["QUIT","Q"]:
        break

    elif action in ["HELP","H"]:
        print("This is Bateman's 4chan scraper. It saves attachments from threads whose OPs contain a keyword of interest that is being searched for. Special requests can be made")
        print("The file 'scraperconfig.txt' stores the program's config in the program's directory")
        print("Scraped files are saved in nested directories in the same directory as the program")
        print()
        print("SCRAPE     /  S: Saves files from threads whose OP contains a keyword of interest. Thread OPs from scraped threads are saved until they appear in the archive for one final thread scrape")
        print("SCRAPEQUIT / SQ: Scrapes then closes the program")
        print("REQUEST    /  R: Toggle the scraping of a specially requested thread. Requests override the blacklist")
        print("BLACKLIST  /  B: Toggle the blacklisting of a thread to not be scraped by supplying the OP number")
        print("VIEW       /  V: View the keywords that are currently being searched for")
        print("ADD        /  A: Add keywords to search for. This is per board and keywords are separated by spaces. To search for a phrase keyword eg 'American Psycho' input 'american_psycho' ")
        print("DELETE     /  D: Delete keywords to no longer search for")
        print("HELP       /  H: Shows this help text")
        print("QUIT       /  Q: Closes the program")

    elif action in ["SCRAPE","S"]:
        scrape()

    elif action in ["SCRAPEQUIT","SQ"]:
        scrape()
        break

    elif action in ["REQUEST","R"]:
        viewrequests()
        print('\n')
        requestboard = input("Which board is the thread on? ").lower().strip()
        if requestboard == "":
            print("No board supplied")
            continue
        try:
            requestopno = int(input("What is the OP number of the requested thread? ").strip())
        except:
            print("Error: Invalid number")
            continue
        requestkeyword = input("What keyword(s) to tag folder with? ").lower().replace("_"," ").strip()
        if requestkeyword == "":
            requestkeyword = "request"
        if not requestboard in configjson["scrapednos"]:
            configjson["scrapednos"][requestboard]=[]
        if not [requestboard,requestopno,requestkeyword] in configjson["specialrequests"]:
            configjson["specialrequests"].append([requestboard,requestopno,requestkeyword])
            print("Thread /"+requestboard+"/:"+str(requestopno)+":"+requestkeyword+" added to special requests")
        else:
            configjson["specialrequests"].remove([requestboard,requestopno,requestkeyword])
            print("Thread /"+requestboard+"/:"+str(requestopno)+":"+requestkeyword+" removed from special requests")
        saveconfig()

    elif action in ["BLACKLIST","B","BLACK","BL"]:
        viewblacklisting()
        print('\n')
        blacklistboard = input("Which board is the thread on? ").lower().strip()
        if blacklistboard == "":
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
            print("Now blacklisting /"+blacklistboard+"/:"+str(blacklistopno))
        else:
            configjson["blacklistedopnos"][blacklistboard].remove(blacklistopno)
            print("No longer blacklisting /"+blacklistboard+"/:"+str(blacklistopno))
        saveconfig()

    elif action in ["VIEW","V"]:
        viewscraping()
        print('\n')
        viewrequests()
        print('\n')
        viewblacklisting()

    elif action in ["ADD","A"]:
        viewscraping()
        print('\n')
        boardtomodify = input("Which board to add keywords to? ").lower().strip()
        if boardtomodify == "":
            print("No board supplied")
            continue
        if not boardtomodify in configjson["keywords"]:
            boardtomodifyarchive = input("Does /"+boardtomodify+"/ have an archive? (Y/N) ").upper().strip()
            if not boardtomodifyarchive in ["Y","N"]:
                print("Error: Expected Y or N")
                continue
        else:
            boardtomodifyarchive = "OLD"
        keywordstoadd = input("Which keywords to start scraping for? ").lower().split()
        keywordstoadd = [keyword.replace("_"," ").strip() for keyword in keywordstoadd if keyword.replace("_"," ").strip() != ""]
        if not keywordstoadd:
            if boardtomodify in configjson["keywords"]:
                print("No more keywords added for /"+boardtomodify+"/")
            else:
                print("No keywords added for /"+boardtomodify+"/, not scraping it")
            continue
        if not boardtomodify in configjson["keywords"]:
            configjson["keywords"][boardtomodify]=[]
        if boardtomodifyarchive == "N":
            configjson["noarchiveboards"].append(boardtomodify)
        if not boardtomodify in configjson["lastscrapeops"]:
            configjson["lastscrapeops"][boardtomodify]=[]
        if not boardtomodify in configjson["blacklistedopnos"]:
            configjson["blacklistedopnos"][boardtomodify]=[]
        if not boardtomodify in configjson["scrapednos"]:
            configjson["scrapednos"][boardtomodify]=[]
        for keyword in keywordstoadd:
            if not keyword in configjson["keywords"][boardtomodify]:
                configjson["keywords"][boardtomodify].append(keyword)
        print("Keywords for /"+boardtomodify+"/ updated to:",end=" ")
        for keyword in configjson["keywords"][boardtomodify][:-1]:
            print("'"+keyword,end="', ")
        print("'"+configjson["keywords"][boardtomodify][-1]+"'")
        saveconfig()

    elif action in ["DELETE","DEL","D"]:
        if not configjson["keywords"]:
            print("Currently not scraping any boards")
            continue
        viewscraping()
        print('\n')
        boardtomodify = input("Which board to delete keywords from? ").lower().strip()
        if boardtomodify == "":
            print("No board supplied")
            continue
        if not boardtomodify in configjson["keywords"]:
            print("Currently not scraping /"+boardtomodify+"/")
            continue
        keywordstodel=input("Which keywords to stop scraping for? ").lower().split()
        keywordstodel = [keyword.replace("_"," ").strip() for keyword in keywordstodel if keyword.replace("_"," ").strip() != ""]
        if not keywordstodel:
            print("No keywords removed for /"+boardtomodify+"/")
            continue
        for keyword in keywordstodel:
            if keyword in configjson["keywords"][boardtomodify]:
                configjson["keywords"][boardtomodify].remove(keyword)
        if not configjson["keywords"][boardtomodify]:
            print("Stopped scraping /"+boardtomodify+"/")
            del configjson["keywords"][boardtomodify]
            if boardtomodify in configjson["noarchiveboards"]:
                configjson["noarchiveboards"].remove(boardtomodify)
        else:
            print("Keywords for /"+boardtomodify+"/ updated to:",end=" ")
            for keyword in configjson["keywords"][boardtomodify][:-1]:
                print("'"+keyword,end="', ")
            print("'"+configjson["keywords"][boardtomodify][-1]+"'")
        saveconfig()

    else:
        print("Unknown command")

################################################################################


