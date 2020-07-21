from sys import stdout
from math import floor

msg = ""
pos = 0
of = 10
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
    printmsg()
    printprog()
    active = True
    if 'tick' in kwargs:
        tick()

def printmsg():
    global msg
    stdout.write(msg)
    stdout.flush()

def printprog():
    global pos, of, bsnum
    hashund = ('#'*floor(10*(pos/of))).ljust(10,'_')
    prog = '[{}] ({}/{})'.format(hashund,pos,of)
    bsnum = len(prog)
    stdout.write(prog)
    stdout.flush()

def tick():
    global pos, of, bsnum, active
    pos+=1
    stdout.write('\b'*bsnum)
    stdout.flush()
    printprog()
    if pos == of:
        stdout.write('\n')
        stdout.flush()
        active = False

def finish():
    global active
    if active:
        stdout.write('\n')
        stdout.flush()
        active = False

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
    finish()
    finish()
    # for i in range(10):
    #     sleep(0.5)
    #     progmsg(msg='Error',tick=True)
    input('End is here')
