"""Independent byte-bank transition reference and leaf/caller MIPS oracle."""
import itertools

from tools.experiments import game_color_state_submit as source
from tools.tests import game_sequence_state_reset_oracle as reset
from tools.tests.game_sequence_event_scan_oracle import load_signed_byte

put,read,signed,STACK=reset.put,reset.read,reset.signed,reset.STACK
MASK=0xFFFFFFFF
BASE,LENGTH,SLOTS=0x800DDD90,0xB0,0x800DD2B0
NAMES=('colors','modes','ticks','busy','limits')
GLOBALS=dict(colors=0x800DDDA0,modes=0x800DDDAC,ticks=0x800DDDB0,busy=0x800DDDC0,limits=0x800DDE28)
SYMBOLS=dict(zip(('D_800DDDA0','D_800DDDAC','D_800DDDB0','D_800DDDC0','D_800DDE28'),GLOBALS.values()))
TIMES=((0,0),(0,1),(1,0),(-1,0),(-0x80000000,0x7FFFFFFF),(0x7FFFFFFF,-0x80000000))
RGB=((0,0,0),(255,128,-1),(0x12345678,-0x80000000,0x7FFFFFFF))


def byte(value):return ((value&255)^128)-128


def fixture(channel=0,mode=0,old=0,times=(0,0),busy=0,duration=0,rgb=(255,128,-1),alias=0,slot_state=0):
    g=dict(GLOBALS)
    if alias==1:g['colors']=g['modes']
    elif alias==2:g['colors']=g['ticks']
    elif alias==3:g['modes']=g['busy']
    elif alias==4:g['ticks']=g['limits']
    elif alias==5:g['colors']=g['limits']
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x180,0x100)}
    memory.update({BASE+i:(i*13+0xA5)&255 for i in range(LENGTH)})
    memory.update({SLOTS+i:0xA5 for i in range(16)})
    for i in range(4):
        put(memory,g['modes']+i,(old+i)&255,1);put(memory,g['ticks']+i*4,(times[0]+i)&MASK)
        put(memory,g['limits']+i*4,(times[1]+i)&MASK);put(memory,g['busy']+i,busy,1)
    put(memory,g['modes']+channel,old&255,1);put(memory,g['ticks']+channel*4,times[0]&MASK)
    put(memory,g['limits']+channel*4,times[1]&MASK);put(memory,g['busy']+channel,busy,1)
    put(memory,SLOTS+channel,slot_state&255,1)
    return memory,tuple(v&MASK for v in (*rgb,duration,mode,channel)),g


def cases(native=False):
    for channel,mode,other,timing,busy,duration_index in itertools.product(range(4),(-128,-1,0,1,127),
            (False,True),range(len(TIMES)),(0,1,255),(0,1)):
        yield fixture(channel,mode,17 if other else mode,TIMES[timing],busy,
            (0,-1,-0x80000000,0x7FFFFFFF)[(timing+duration_index)%4],RGB[timing%3])
    for alias,channel,mode,timing,busy in itertools.product(range(1,6),range(4),(-128,-1,0,1,127),(0,1),(0,255)):
        yield fixture(channel,mode,mode,TIMES[timing],busy,-1,RGB[2],alias)
    if not native:
        for channel,mode in itertools.product(range(4),(0x1234FFFF,0x80000080,0xFFFFFF7F,0x100)):
            yield fixture(channel,mode,byte(mode),(1,0))


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x180<=a<STACK+0x100}


def apply(memory,args,g):
    red,green,blue,duration,mode,channel=args;mode=byte(mode)
    same=mode==byte(read(memory,g['modes']+channel,1))
    complete=signed(read(memory,g['ticks']+channel*4))>=signed(read(memory,g['limits']+channel*4))
    idle=read(memory,g['busy']+channel,1)==0
    if same and complete and idle:return False
    color=g['colors']+channel*3
    stores=((color+1,green,1),(color+2,blue,1),(color,red,1),
        (g['limits']+channel*4,duration,4),(g['ticks']+channel*4,0,4),
        (g['modes']+channel,mode,1),(g['busy']+channel,0,1))
    for at,value,width in stores:put(memory,at,value&((1<<(width*8))-1),width)
    return True


def reference(memory,args,g):
    result=dict(memory);changed=apply(result,args,g);return result,changed


def pair_reference(memory,channel,g):
    result=dict(memory);calls=[]
    if read(result,SLOTS+channel,1)!=255:
        put(result,SLOTS+channel,255,1)
        for duration,mode in ((0,1),(50,0)):
            args=(0,0,0,duration,mode,channel);calls.append((source.ENTRY,args));apply(result,args,g)
    return result,calls


class ColorOracle(reset.machine.InitializeOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,helpers=None):
        super().__init__(words,memory,args,helpers or {},phase,entry=entry)

    def execute(self,word):
        if word>>26==32:load_signed_byte(self,word)
        else:super().execute(word)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unknown color caller target')
        packet=self.arguments(6);self.calls.append((target,packet));self.events.append(('CALL',target,packet))

    def hook(self,target):raise ValueError('Color chain unexpectedly reached an opaque hook')
