from sys import stdout
from time import sleep
import threading

################################################################################

class progressmsg():
    """Progress message: message with progress bar and counter"""
    def __init__(self,hashOrBlock=False):
        """$hashOrBlock determines progress bar style, False for hashes and underscores, True for unicode blocks and spaces. The latter is doubly as precise as the former."""
        self.__resetvars()
        self.__hashOrBlock = hashOrBlock

    def __resetvars(self):
        # resets variables that relate to current progress; hashOrBlock stays constant across whole instance lifespan
        self.__msg = ""
        self.__pos = 0
        self.__of = 1
        self.__endmsg = ""
        self.__active = False

    def __printprog(self):
        if not self.__hashOrBlock:
            hashesAndUnderscores = ("#"*int(10*(self.__pos/self.__of))).ljust(10,"_")
            progressText = "[{}] ({}/{})".format(hashesAndUnderscores,self.__pos,self.__of)
        else:
            numberOfHalfBars = int(20*(self.__pos/self.__of))
            barsAndSpaces = ("\u2588"*int(numberOfHalfBars/2)+("\u258C" if numberOfHalfBars % 2 else "")).ljust(10," ")
            progressText = "|{}| ({}/{})".format(barsAndSpaces,self.__pos,self.__of)
        self.__blen = len(progressText)
        stdout.write(progressText)
        stdout.flush()

    def progressmsg(self,msg=None,pos=None,of=None,endmsg=None,ticknow=False):
        """Print the progress message"""
        if self.__active:
            stdout.write("\n")
        if msg is not None:
            self.__msg = msg
        if pos is not None:
            self.__pos = pos
        if of is not None:
            self.__of = of
        if endmsg is not None:
            self.__endmsg = endmsg
        stdout.write(self.__msg)
        self.__printprog()
        self.__active = True
        if ticknow:
            self.tick()

    def tick(self,times=1):
        """Advance the progress by 1 if active"""
        if self.__active:
            stdout.write("\b"*self.__blen)
            self.__pos = min([self.__pos + times,self.__of])
            self.__printprog()
            if self.__pos == self.__of:
                self.finish()

    def finish(self,endmsg=None):
        """New line and reset instance, option to override endmsg"""
        if isinstance(endmsg,str):
            self.__endmsg = endmsg
        if self.__active:
            stdout.write(self.__endmsg+"\n")
            stdout.flush()
        self.__resetvars()
