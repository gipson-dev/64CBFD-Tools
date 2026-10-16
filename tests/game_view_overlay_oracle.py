"""Full-word view addresses, signed helper arguments and live overlay state."""
from collections import Counter
import itertools

from tools.experiments import game_view_overlay_pass as source
from tools.tests import game_view_render_pass_oracle as machine

put,read,half,STACK=machine.put,machine.read,machine.half,machine.STACK
BASE,PAGE,CATEGORY,TABLE,MATRIX,CURSOR=0x800BE628,0x800BE9C0,0x800BE9F0,0x800DC2A0,0x80089470,0x50020
SETUP,CATEGORY_PASS,MODE_PASS=0x1501A490,0x1502BAD0,0x151674F8
SIGNATURES={SETUP:6,CATEGORY_PASS:3,MODE_PASS:4}


def fixture(page=0,category=0x1D,pattern=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for address,size in ((BASE-4,12),(PAGE-4,9),(CATEGORY-4,12),(TABLE-4,1032),(0x50000,4096)):
        memory.update({address+i:0xA5 for i in range(size)})
    put(memory,BASE,(0x80401234,0xFFFFFEFC,0x12348004,0x80007FFC)[pattern%4])
    memory[PAGE]=page;put(memory,CATEGORY,category&0xFFFFFFFF)
    for i in range(256):put(memory,TABLE+4*i,(0x81200000+i*0x1000)&0xFFFFFFFF)
    return memory


def public(memory):
    return {a:b for a,b in memory.items() if not STACK-0x400<=a<STACK+0x100}


def snapshot(memory):
    value=2166136261
    for i in range(128):value=((value^read(memory,0x50000+i*4))*16777619)&0xFFFFFFFF
    return read(memory,BASE),memory[PAGE],read(memory,CATEGORY),value


def returned(target,args,ordinal,pattern):
    return (args[0]+8*(1+(target//4+ordinal+pattern)%3))&0xFFFFFFFF


def effect(memory,target,ordinal,mode):
    if mode==1 and target==SETUP:
        put(memory,BASE,0x80507FFC);memory[PAGE]=255;put(memory,CATEGORY,0x1D)
    elif mode==2 and target==SETUP:
        put(memory,CATEGORY,0x1001D);memory[PAGE]=128
    elif mode==3 and target==MODE_PASS and ordinal==2:
        put(memory,BASE,0xFFFFFF80);memory[PAGE]=1;put(memory,TABLE+4,0x12348004)
    elif mode==4 and target==MODE_PASS and ordinal==1:
        put(memory,BASE,0x81718004);memory[PAGE]=128
    else:return False
    return True


def reference(memory,view=0,pattern=0,mode=0,cursor=CURSOR):
    memory,calls,observations,fired=dict(memory),[],[],[]
    counts=Counter();emitted=0
    view&=0xFFFFFFFF
    def call(target,*args):
        args=tuple(a&0xFFFFFFFF for a in args)
        calls.append((target,args));observations.append((target,snapshot(memory)))
        counts[target]+=1
        value=returned(target,args,counts[target],pattern)
        if effect(memory,target,counts[target],mode):fired.append((target,counts[target],mode))
        return value
    def emit(w0,w1):
        nonlocal cursor,emitted
        put(memory,cursor,w0);put(memory,cursor+4,w1&0xFFFFFFFF);cursor+=8;emitted+=1
        if mode==5 and emitted==4:
            memory[PAGE]=255;fired.append(('late-page',1,mode))
    emit(0xDC080008,read(memory,BASE)+view*0x180+memory[PAGE]*16+64)
    cursor=call(SETUP,cursor,half(view),0,0,0,0)
    emit(0xDA380003,MATRIX)
    emit(0xDA380007,read(memory,BASE)+view*0x180+memory[PAGE]*64+256)
    if read(memory,CATEGORY)==0x1D:cursor=call(CATEGORY_PASS,cursor,6,half(view))
    cursor=call(MODE_PASS,cursor,5,0,0)
    cursor=call(MODE_PASS,cursor,5,0,1)
    emit(0xDA380007,read(memory,BASE)+view*0x180+memory[PAGE]*64+256)
    emit(0xDA380005,read(memory,TABLE+memory[PAGE]*4)+view*64)
    return memory,calls,observations,fired,cursor


def corpus():
    for view,page,category,pattern,mode in itertools.product(
            (0,1,0x7FFF,0x8000,0xFFFF,0x10001,0x80000001,0xFFFFFFFF),
            (0,1,128,255),(0,0x1D,0x1001D,0xFFFFFFFF),range(2),range(6)):
        yield fixture(page,category,pattern),view,pattern,mode
    for byte in range(256):yield fixture(byte,0x1D,byte%4),0xA55A8001,byte%4,0


class OverlayOracle(machine.RenderOracle):
    def __init__(self,words,memory,view=0,pattern=0,mode=0,phase=0,entry=source.ENTRY,arguments=None,connected=None):
        super().__init__(words,memory,0,pattern,phase=phase,entry=entry,
            arguments=arguments or (CURSOR,view),connected=connected)
        self.overlay_mode,self.emitted=mode,0

    def put(self,address,value,size):
        super().put(address,value,size)
        if getattr(self,'own_instruction',False) and 0x50000<=address<0x51000 and size==4:
            self.emitted+=1
            if self.overlay_mode==5 and self.emitted==8:
                self.memory[PAGE]=255;self.fired.append(('late-page',1,5))

    def record_call(self,target):
        args=self.arguments(SIGNATURES[target]);self.calls.append((target,args))
        self.events.append(('CALL',target,args));self.observations.append((target,snapshot(self.memory)))
        self.counts[target]+=1

    def hook(self,target):
        value=returned(target,self.calls[-1][1],self.counts[target],self.pattern)
        if effect(self.memory,target,self.counts[target],self.overlay_mode):
            self.fired.append((target,self.counts[target],self.overlay_mode))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=value
