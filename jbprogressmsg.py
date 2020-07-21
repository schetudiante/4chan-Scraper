from sys import stdout
from math import floor

def resetglobals():
    global msg,pos,of,bsnum,active
    msg = ""
    pos = 0
    of = 1
    bsnum = 0
    active = False

def progmsg(*args,**kwargs):
    global msg, pos, of, active
    if 'msg' in kwargs:
        msg = kwargs['msg']
    if 'pos' in kwargs:
        pos = int(kwargs['pos'])
    if 'of' in kwargs:
        of = kwargs['of']
    if active == True:
        stdout.write('\n')
        stdout.flush()
    _printmsg()
    _printprog()
    active = True
    if 'tick' in kwargs:
        tick()

def _printmsg():
    global msg
    stdout.write(msg)
    stdout.flush()

def _printprog():
    global pos, of, bsnum
    hashund = ('#'*floor(10*(pos/of))).ljust(10,'_')
    prog = '[{}] ({}/{})'.format(hashund,pos,of)
    bsnum = len(prog)
    stdout.write(prog)
    stdout.flush()

def tick():
    global pos, of, bsnum
    pos+=1
    stdout.write('\b'*bsnum)
    stdout.flush()
    _printprog()
    if pos == of:
        finish()

def finish():
    global active
    if active:
        stdout.write('\n')
        stdout.flush()
    resetglobals()

################################################################################

#When Module Loaded
resetglobals()

################################################################################

#Debug Example
if __name__ == '__main__':
    from time import sleep
    progmsg(msg='Doing shit ',of=20)
    for i in range(5):
        sleep(0.5)
        tick()

    progmsg(msg='Doing more shit ')
    for i in range(5):
        sleep(0.5)
        tick()
    # finish()
    # finish()
    for i in range(10):
        sleep(0.5)
        progmsg(msg='Already done ',tick=True)
    input('End is here')

################################################################################
