from time import time
import shutil
import json
import os

################################################################################

class configmanager():
    """SAO Config Manager:
    For managing a JSON file with easy commands, automatic saving, and a few custom data structures
    Current custom data structures: Delta Systems, Tiered Progress Tracker"""

    # Common methods / functions

    def __init__(self, filename = "config.json", default = {}):
        """Load or create config at $filename and initialise configmanager instance
        Autosaving is enabled by default"""
        self.filename = filename
        # tpt_ settings
        self.tpt_manageDirectories = False
        self.tpt_manageDirectoriesDeleteEmptyOnUpdate = False
        self.tpt_noPromotingNewBlacklistedOrDone = True
        try:
            with open(self.filename) as config_jsonfile:
                self.config = json.load(config_jsonfile)
        except json.decoder.JSONDecodeError:
            try:
                corruptedNewFilename = "{}.CORRUPTED_{}".format(self.filename,self.timestamp())
                os.rename(self.filename,corruptedNewFilename)
                print("Error: corrupted config \'{}\' detected, renamed to \'{}\'".format(self.filename,corruptedNewFilename))
            except:
                print("Error: corrupted config \'{}\' detected, could not rename and salvage".format(self.filename))
            self.config = default
            self.save()
            print("Created config file \'{}\'".format(self.filename))
        except FileNotFoundError:
            self.config = default
            self.save()
            print("Created config file \'{}\'".format(self.filename))
        except Exception as e:
            print("Unexpected error {} has occurred, please let SAO know!".format(e))
            self.config = default
            self.save()
            print("Created config file \'{}\'".format(self.filename))

    def save(self):
        """Method to save config at $self.filename"""
        with open(self.filename,'w') as config_jsonfile:
            config_jsonfile.write(json.dumps(self.config))

    def timestamp(self):
        """Returns integer timestamp in seconds since Unix Epoch"""
        return int(time())

    def __touchPathCoreAndReturnWithPathEnd(self, path):
        """Touches the core of the path supplied, creating empty dictionaries along the way if necessary
        Returns the live version of the dictionary at the core path, and the path end name"""
        path = path.lower().split("/")
        pathcore = self.config
        for key in path[:-1]:
            pathcore = pathcore.setdefault(key,{})
        return pathcore,path[-1]

    def __getPathCoreAndReturnWithPathEnd(self, path):
        """Tries to get the live version of the dictionary at the path core
        Raises an exception if the core path does not exist
        Returns the live version of the dictionary at the core path, and the path end name, if no exception"""
        path = path.lower().split("/")
        pathcore = self.config
        for key in path[:-1]:
            pathcore = pathcore[key] # exception will be raised if can't get
        return pathcore,path[-1]

    def valueTouch(self, path, default = None):
        """Touches the entry at $path
        If no entry exists at $path then $default is set there
        Returns the touched value"""
        pathcore,pathend = self.__touchPathCoreAndReturnWithPathEnd(path)
        value = pathcore.setdefault(pathend,default)
        return value

    def valueSet(self, path, value = None):
        """Sets the entry at $path to $value
        Returns the set value"""
        pathcore,pathend = self.__touchPathCoreAndReturnWithPathEnd(path)
        pathcore[pathend] = value
        return value

    def valueGet(self, path):
        """Tries to get the value at $path
        Raises an exception if $path does not exist
        Returns the got value if no exception"""
        pathcore,pathend = self.__getPathCoreAndReturnWithPathEnd(path)
        value = pathcore[pathend] # exception will be raised if can't get
        return value

    def valuePing(self, path):
        """Tries valueGet at $path
        Tests for presence of entry at $path
        Returns True if successful else False"""
        try:
            self.valueGet(path)
            return True
        except:
            return False

    def valueMove(self, pathFrom, pathTo):
        """Attempts to move the value at $pathFrom to $pathTo
        Raises an exception if no value at $pathFrom exists, else returns the moved value"""
        if pathFrom == pathTo:
            return self.valueTouch(pathTo)

        toMoveFromCore,toMoveFromEnd = self.__getPathCoreAndReturnWithPathEnd(pathFrom) # will raise exception if pathFrom core does not exist
        valueToMove = toMoveFromCore[toMoveFromEnd] # will raise exception if pathFrom end does not exist
        toMoveToCore,toMoveToEnd = self.__touchPathCoreAndReturnWithPathEnd(pathTo)
        toMoveToCore[toMoveToEnd] = valueToMove
        del toMoveFromCore[toMoveFromEnd]
        return toMoveToCore[toMoveToEnd]

    def valueDelete(self, path):
        """Touches the core of $path and tries to remove the key at the end of $path
        Returns the value removed else None if nothing existed at $path
        (yes this conflates removing value 'None' with returning 'None' because nothing was removed...)"""
        pathcore,pathend = self.__touchPathCoreAndReturnWithPathEnd(path)
        try:
            return_value = pathcore[pathend]
            del pathcore[pathend]
        except KeyError:
            return_value = None
            pass
        return return_value

    # File/Folder Manager
    """Some scripts for moving files and folders around, useful to keep config manager paths in sync with file system paths"""
    def ffm_makedirs(self, path):
        """Does os.makedirs($path) with exist_ok=True"""
        os.makedirs(path, exist_ok=True)

    def ffm_tryMove(self, pathFrom, pathTo):
        """Tries to move the folder or file at $pathFrom to $pathTo
        Returns True if successful else False"""
        try:
            shutil.move(pathFrom, pathTo)
            return True
        except:
            return False

    def ffm_rmIfEmptyTree(self, path, ignore=["desktop.ini"]):
        """If the directory at $path is an empty tree* (a tree of directories containing no files) then remove it. *ignoring files with their name in the list $ignore
        Returns True if a tree is removed else False"""
        if not [file for _,_,files in os.walk(path) for file in files if not file in ignore]:
            shutil.rmtree(path,ignore_errors=True)
            return True
        else:
            return False

    # Tiered Progress Tracker
    """For storing data in different 'tiers', promoting and demoting as desired, also allows blacklisting and whitelisting of entries, and a 'done' list.
    Particularly useful for keeping track of 'tasks': progress / work done on each task, prioritising / ordering tasks by importance, blacklisting and whitelisting task ids + task keywords, and keeping a record of completed task ids
    A Tiered Progress Tracker system (or 'tpt' system for short) is a dictionary that consists of:
    'tiers': an ordered dictionary of tiers (ordered from lowest to highest tier), each of which contains entries which we shall call 'tasks'
    'keywords_wl': a whitelist for task keywords
    'idnos_bl': a blacklist for task idnos
    'idnos_done': a list of task idnos that have been completed

    The methods below are each documented about how they work and their uses

    Implementations of the ffm_ methods can also be enabled to keep task folders in sync with the config: check the 'tpt_ settings' section of __init__() for settings"""

    def tpt_touch(self, path, defaultTiers=["normal","special"]):
        """Touches the tpt at $path
        If no entry exists at $path then the default tpt is made there
        Does not override the entry at $path even if it is not a tpt
        Default tiers can be specified here
        If self.tpt_manageDirectories == True then self.ffm_makedirs will make directories to $path in the cwd"""
        if self.tpt_manageDirectories:
            self.ffm_makedirs(path)
        return self.valueTouch(path,default={"keywords_wl":[], "idnos_bl":[], "idnos_done":[], "tiers":{tier:[] for tier in defaultTiers}})

    def tpt_getkeywords_wl(self, path):
        """Touches the tpt at $path and returns the tpt's keywords_wl list"""
        tpt_system = self.tpt_touch(path)
        return tpt_system["keywords_wl"]

    def tpt_getidnos_bl(self, path):
        """Touches the tpt at $path and returns the tpt's idnos_bl list"""
        tpt_system = self.tpt_touch(path)
        return tpt_system["idnos_bl"]

    def tpt_getidnos_done(self, path):
        """Touches the tpt at $path and returns the tpt's idnos_done list"""
        tpt_system = self.tpt_touch(path)
        return tpt_system["idnos_done"]

    def tpt_gettiersList(self, path):
        """Touches the tpt at $path and returns the tpt's tiers as a list"""
        tpt_system = self.tpt_touch(path)
        return [t for t in tpt_system["tiers"]]

    def tpt_keywords_wlAdd(self, path, keywords):
        """Touches the tpt at $path and merges the tpt's keywords_wl with $keywords
        Returns a (sorted) list of the keywords added"""
        tpt_system = self.tpt_touch(path)
        return_keywordsAdded = []
        for keyword in keywords:
            keyword = self.tpt_sanitiseKeyword(keyword)
            if not keyword:
                continue
            if not keyword in tpt_system["keywords_wl"]:
                tpt_system["keywords_wl"].append(keyword)
                return_keywordsAdded.append(keyword)
        tpt_system["keywords_wl"].sort()
        return_keywordsAdded.sort()
        return return_keywordsAdded

    def tpt_keywords_wlRemove(self, path, keywords):
        """Touches the tpt at $path and removes any keywords in $keywords from the tpt's keywords_wl
        Returns a (sorted) list of the keywords removed"""
        tpt_system = self.tpt_touch(path)
        return_keywordsRemoved = []
        for keyword in keywords:
            keyword = self.tpt_sanitiseKeyword(keyword)
            if not keyword:
                continue
            try:
                tpt_system["keywords_wl"].remove(keyword)
                return_keywordsRemoved.append(keyword)
            except:
                pass
        tpt_system["keywords_wl"].sort()
        return_keywordsRemoved.sort()
        return return_keywordsRemoved

    def tpt_idnos_blAdd(self, path, idnos):
        """Touches the tpt at $path and merges the tpt's idnos_bl with $idnos
        Returns a (sorted) list of the idnos added"""
        tpt_system = self.tpt_touch(path)
        return_idnosAdded = []
        for idno in idnos:
            if not idno in tpt_system["idnos_bl"]:
                tpt_system["idnos_bl"].append(idno)
                return_idnosAdded.append(idno)
        tpt_system["idnos_bl"].sort()
        return_idnosAdded.sort()
        return return_idnosAdded

    def tpt_idnos_blRemove(self, path, idnos):
        """Touches the tpt at $path and removes any idnos in $idnos from the tpt's idnos_bl
        Returns a (sorted) list of the idnos removed"""
        tpt_system = self.tpt_touch(path)
        return_idnosRemoved = []
        for idno in idnos:
            try:
                tpt_system["idnos_bl"].remove(idno)
                return_idnosRemoved.append(idno)
            except:
                pass
        tpt_system["idnos_bl"].sort()
        return_idnosRemoved.sort()
        return return_idnosRemoved

    def tpt_idnos_blToggle(self, path, idnos):
        """Touches the tpt at $path and toggles idnos in $idnos from the tpt's idnos_bl
        Returns a tuple of (sorted) lists, those idnos removed, and those added"""
        tpt_system = self.tpt_touch(path)
        return_idnosRemoved = []
        return_idnosAdded = []
        for idno in idnos:
            try:
                tpt_system["idnos_bl"].remove(idno)
                return_idnosRemoved.append(idno)
            except:
                tpt_system["idnos_bl"].append(idno)
                return_idnosAdded.append(idno)
        tpt_system["idnos_bl"].sort()
        return_idnosRemoved.sort()
        return_idnosAdded.sort()
        return return_idnosRemoved,return_idnosAdded

    def tpt_getTaskAndTierByIdno(self, path, idno):
        """Touches the tpt at $path
        Returns a 2-tuple: the task with idno=$idno, and its tier if it exists; else returns None,None"""
        tpt_system = self.tpt_touch(path)
        for tier,tierTasks in tpt_system["tiers"].items():
            for task in tierTasks:
                if task[0] == idno:
                    return task,tier
        return None,None

    def tpt_getTaskByIdno(self, path, idno):
        """Touches the tpt at $path
        Returns the task with idno=$idno if it exists, else returns None"""
        return self.tpt_getTaskAndTierByIdno(path,idno)[0]

    def tpt_getTaskTierByIdno(self, path, idno):
        """Touches the tpt at $path
        Returns the tier that the task with idno=$idno has, else returns None if task not found"""
        return self.tpt_getTaskAndTierByIdno(path,idno)[1]

    def tpt_getTasksInTier(self, path, tier):
        """Touches the tpt at $path and returns a list of the tasks in tier=$tier"""
        tpt_system = self.tpt_touch(path)
        return tpt_system["tiers"][tier]

    def tpt_promoteTaskByIdno(self, path, idno, keyword = None):
        """Promotes a task up a tier if a higher tier exists. Promotes new tasks to lowest tier.
        If $keyword is a string then the task's keyword is overriden by $keyword, else the task's existing keyword is prefixed with "_PROMOTED_". Note at most one prefix appears before a keyword (prefixes do not accumulate).
        Returns a 2-tuple: True if a promotion happens else returns False (ie False iff already at top tier), and the task's old keyword"""
        tpt_system = self.tpt_touch(path)
        tpt_system_tiers = tpt_system["tiers"]
        tpt_system_tiersList = list(tpt_system_tiers)

        task,tier_current = self.tpt_getTaskAndTierByIdno(path,idno)
        if tier_current is None:
            # new task
            if (idno in tpt_system["idnos_bl"] or idno in tpt_system["idnos_done"]) and self.tpt_noPromotingNewBlacklistedOrDone:
                return False,None
            else:
                keyword_old = None
                task = [idno,"_NEW_",[]]
                tier_promotion = tpt_system_tiersList[0]
                return_value = True
        else:
            # promoting existing
            tpt_system_tiers[tier_current].remove(task)
            keyword_old = task[1]
            if tier_current == tpt_system_tiersList[-1]:
                # top tier, stay here
                tier_promotion = tier_current
                return_value = False
            else:
                # not top tier, move up
                tier_promotion = tpt_system_tiersList[1 + tpt_system_tiersList.index(tier_current)]
                return_value = True

        task = self.__tpt_modifyTaskKeyword(path,task,keyword,"PRO")
        tpt_system_tiers[tier_promotion].append(task)
        return return_value,keyword_old

    def tpt_demoteTaskByIdno(self, path, idno, keyword = None):
        """Demotes a task down a tier if the task exists. Removes a task if it is already at the lowest tier.
        If $keyword is a string then the task's keyword is overriden by $keyword, else the task's existing keyword is prefixed with "_DEMOTED_". Note at most one prefix appears before a keyword (prefixes do not accumulate).
        Returns a 2-tuple: True if a demotion happens else returns False (ie False iff task doesn't exist), and the task's old keyword"""
        tpt_system_tiers = self.tpt_touch(path)["tiers"]
        tpt_system_tiersList = list(tpt_system_tiers)

        task,tier_current = self.tpt_getTaskAndTierByIdno(path,idno)
        if tier_current is None:
            # not found
            return False,None
        else:
            # demote to lower tier
            keyword_old = task[1]
            tpt_system_tiers[tier_current].remove(task)
            if tier_current != tpt_system_tiersList[0]:
                # if not lowest tier removed
                tier_demotion = tpt_system_tiersList[-1 + tpt_system_tiersList.index(tier_current)]
                task = self.__tpt_modifyTaskKeyword(path,task,keyword,"DE")
                tpt_system_tiers[tier_demotion].append(task)
            return True,keyword_old

    def tpt_promoteTaskToByIdno(self, path, idno, keyword = None, promotionTier = None):
        """Promotes a task up to $promotionTier if the task is in a strictly lower tier (or does not exist yet). Keywords are assigned if promotion happens, or 'softly' if promoting to same tier (keyword can be overriden, but will not be prefixed with _PROMOTED_ if staying on same tier).
        Returns a 2-tuple: True if a promotion happens else returns False, and the task's old keyword"""
        tpt_system = self.tpt_touch(path)
        tpt_system_tiers = tpt_system["tiers"]
        tpt_system_tiersList = list(tpt_system_tiers)

        task,currentTier = self.tpt_getTaskAndTierByIdno(path,idno)
        try:
            currentTier_index = tpt_system_tiersList.index(currentTier)
        except:
            currentTier_index = None
        promotionTier_index = tpt_system_tiersList.index(promotionTier)

        if currentTier_index is None:
            # new task
            keyword_old = None
            if (idno in tpt_system["idnos_bl"] or idno in tpt_system["idnos_done"]) and self.tpt_noPromotingNewBlacklistedOrDone:
                return_value = False
            else:
                task = [idno,"_NEW_",[]]
                task = self.__tpt_modifyTaskKeyword(path,task,keyword,"PRO")
                tpt_system_tiers[promotionTier].append(task)
                return_value = True
        elif currentTier_index <= promotionTier_index:
            # task present and tier less than or equal to promotionTier
            keyword_old = task[1]
            tpt_system_tiers[currentTier].remove(task)
            task = self.__tpt_modifyTaskKeyword(path,task,keyword,"PRO")
            tpt_system_tiers[promotionTier].append(task)
            if currentTier_index == promotionTier_index:
                return_value = False
            else:
                return_value = True
        else:
            # task present and tier strictly greater than promotionTier
            keyword_old = task[1]
            return_value = False

        return return_value,keyword_old

    def tpt_demoteTaskToByIdno(self, path, idno, keyword = None, demotionTier = None):
        """Demotes a task down to $demotionTier if the task is in a strictly higher tier. Keywords are assigned if demotion happens, or 'softly' if demoting to same tier (keyword can be overriden, but will not be prefixed with _DEMOTED_ if staying on same tier). $demotionTier must be a valid tier, or None, in which case the method will attempt to remove the task (if it exists).
        Returns a 2-tuple: True if a demotion happens else returns False, and the task's old keyword"""
        tpt_system_tiers = self.tpt_touch(path)["tiers"]
        tpt_system_tiersList = list(tpt_system_tiers)

        task,currentTier = self.tpt_getTaskAndTierByIdno(path,idno)
        try:
            currentTier_index = tpt_system_tiersList.index(currentTier)
        except:
            currentTier_index = None
        try:
            demotionTier_index = tpt_system_tiersList.index(demotionTier)
        except:
            demotionTier_index = None

        if currentTier_index is None:
            # task does not exist
            keyword_old = None
            return_value = False
        else:
            keyword_old = task[1]
            if demotionTier_index is None:
                # removing existing
                tpt_system_tiers[currentTier].remove(task)
                return_value = True
            elif currentTier_index >= demotionTier_index:
                # task present in tier >= demotionTier
                tpt_system_tiers[currentTier].remove(task)
                task = self.__tpt_modifyTaskKeyword(path,task,keyword,"DE")
                tpt_system_tiers[demotionTier].append(task)
                if currentTier_index == demotionTier_index:
                    return_value = False
                else:
                    return_value = True
            else:
                # task present and tier strictly less than demotionTier
                return_value = False

        return return_value,keyword_old

    def tpt_updateTaskByIdno(self, path, idno, entries):
        """Touches the tpt at $path
        If a task with idno=$idno exists in the tpt then its entries are merged with the list $entries
        Returns a list of the new entries added if this update happens, else returns None if no task with idno=$idno exists
        If self.tpt_manageDirectoriesDeleteEmptyOnUpdate == True and if '$path/$idno keyword' is an empty tree of folders then it is removed"""
        tpt_system = self.tpt_touch(path)
        tpt_system_tiers = tpt_system["tiers"]

        for tier in tpt_system_tiers:
            for task in tpt_system_tiers[tier]:
                if task[0] == idno:
                    return_list = []
                    for entry in entries:
                        if not entry in task[2]:
                            task[2].append(entry)
                            return_list.append(entry)
                    if self.tpt_manageDirectories and self.tpt_manageDirectoriesDeleteEmptyOnUpdate:
                        self.ffm_rmIfEmptyTree("{}/{} {}".format(path,idno,task[1]))
                    return return_list
        return None

    def tpt_finishTaskByIdno(self, path, idno):
        """Touches the tpt at $path and adds $idno to the tpt's idnos_done list if it is not already present
        Removes the task with idno=$idno if it exists in any tier
        Returns the task if removed, else returns True if the idno is added to idnos_done, else False if $idno is already in idnos_done"""
        tpt_system = self.tpt_touch(path)
        tpt_system_tiers = tpt_system["tiers"]

        if idno in tpt_system["idnos_done"]:
            return False
        else:
            for tier in tpt_system_tiers:
                for task in tpt_system_tiers[tier]:
                    if task[0] == idno:
                        tpt_system_tiers[tier].remove(task)
                        tpt_system["idnos_done"].append(idno)
                        return task
            tpt_system["idnos_done"].append(idno)
            return True

    def tpt_pruneTasks(self, path, tiers = None, keywords_wl = False, idnos_bl = False, idnos_done = False, demotedPrefixed = False):
        """Removes tasks in the tiers supplied in $tiers from the tpt at $path according to:
        $keywords_wl: those whose keywords are not in keywords_wl
        $idnos_bl: those whose idnos are blacklisted in idnos_bl
        $idnos_done: those whose idnos have been marked as done previously in idnos_done
        $demotedPrefixed: those whose keyword begins with the prefix '_DEMOTED_'
        If $tiers is True then all tiers are pruned
        Returns dictionary of removed tasks"""
        tpt_system = self.tpt_touch(path)
        tpt_system_tiers = tpt_system["tiers"]

        if tiers is True:
            tiers = [t for t in tpt_system_tiers]
        elif tiers is None:
            tiers = []

        tiers = [t for t in tiers if t in tpt_system_tiers]

        tasksRemoved = {tier:[] for tier in tiers}

        if keywords_wl:
            for tier in tiers:
                for task in [t for t in tpt_system_tiers[tier]]:
                    if not task[1] in tpt_system["keywords_wl"]:
                        tpt_system_tiers[tier].remove(task)
                        tasksRemoved[tier].append(task)
        if idnos_bl:
            for tier in tiers:
                for task in [t for t in tpt_system_tiers[tier]]:
                    if task[0] in tpt_system["idnos_bl"]:
                        tpt_system_tiers[tier].remove(task)
                        tasksRemoved[tier].append(task)
        if idnos_done:
            for tier in tiers:
                for task in [t for t in tpt_system_tiers[tier]]:
                    if task[0] in tpt_system["idnos_done"]:
                        tpt_system_tiers[tier].remove(task)
                        tasksRemoved[tier].append(task)
        if demotedPrefixed:
            for tier in tiers:
                for task in [t for t in tpt_system_tiers[tier]]:
                    if task[1].startswith("_DEMOTED_"):
                        tpt_system_tiers[tier].remove(task)
                        tasksRemoved[tier].append(task)

        return tasksRemoved

    def tpt_sanitiseKeyword(self, keyword):
        """Sanitise a keyword by setting to lowercase, replacing underscores with spaces, and stripping trailing whitespace
        Returns $keyword.lower().replace("_"," ").strip()
        This operation is idempotent"""
        return keyword.lower().replace("_"," ").strip()

    def __tpt_modifyTaskKeyword(self, path, task, keyword, depro):
        """Internal code for modifying task's keyword upon promoting or demoting
        $depro either 'PRO' or 'DE'
        Will rename / create directories accordingly if self.tpt_manageDirectories == True"""
        if self.tpt_manageDirectories:
            keyword_old = task[:][1]
        if isinstance(keyword,str):
            task[1] = self.tpt_sanitiseKeyword(keyword)
        elif depro == "PRO":
            if not task[1].startswith("_PROMOTED_"):
                if task[1].startswith("_DEMOTED_"):
                    task[1] = task[1][9:]
                task[1] = "_PROMOTED_" + task[1]
        elif depro == "DE":
            if not task[1].startswith("_DEMOTED_"):
                if task[1].startswith("_PROMOTED_"):
                    task[1] = task[1][10:]
                task[1] = "_DEMOTED_" + task[1]
        if self.tpt_manageDirectories:
            # Tries to rename directories at $path with directory name of form '$idno $keyword_old' to '$idno $keyword_new'
            # Makes new directory anyways if can't move old
            if keyword_old == "_NEW_" or not self.ffm_tryMove("{}/{} {}".format(path,task[0],keyword_old),"{}/{} {}".format(path,task[0],task[1])):
                self.ffm_makedirs("{}/{} {}".format(path,task[0],task[1]))
        return task

################################################################################
