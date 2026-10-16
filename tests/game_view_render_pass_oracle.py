"""Bounded scene-pass contracts, not rendering or hardware emulation."""
from collections import Counter

from tools.experiments import game_view_render_pass as source
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import signed

STACK=machine.STACK
STATE,DISABLED,STOP,MASK,COUNT,BASE,PAGE,MODE=(0x800DBFF0,0x800BEAC0,0x80084480,
    0x800D18A0,0x80082FA0,0x800BE628,0x800BE9C0,0x800BE575)
VIEWS,OTHER,CURSOR=0x30000,0x40000,0x50020
FLAGS=(VIEWS+0x5F0,OTHER+0x5F0)
FIELDS=((STATE,4),(DISABLED,1),(STOP,2),(MASK,2),(COUNT,4),(BASE,4),(PAGE,1),(MODE,1))
SIGNATURES={0x1517EFAC:1,0x1510B7B4:2,0x1515D6D0:2,0x1510B958:1,
    0x1501A490:6,0x151135C4:3,0x151D6778:1,0x151674F8:4,0x15186794:2,
    0x1502BAD0:3,0x15035FE8:2,0x15018E88:2,0x15018F08:2,0x15188D00:3}


def half(value):
    return ((value&65535)^0x8000)-0x8000


def fixture(view=0,count=1,pattern=0,gate=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,length in ((VIEWS-16,4*0x9A0+32),(OTHER-16,4*0x9A0+32),(CURSOR-32,0x1000)):
        memory.update({base+i:0xA5 for i in range(length)})
    for address,size in FIELDS:
        for i in range(-4,size+4):memory[address+i]=0xA5
    for address,value,size in ((STATE,VIEWS,4),(DISABLED,1 if gate==1 else 0,1),
            (STOP,0x8000 if gate==2 else 0,2),(MASK,(1<<half(view)) if gate==4 else 0,2),
            (COUNT,count&0xFFFFFFFF,4),(BASE,0x80401234,4),(PAGE,(0,1,128,255)[pattern%4],1),
            (MODE,(0,1,2,255)[pattern%4],1)):
        put(memory,address,value,size)
    for i in range(4):
        put(memory,FLAGS[0]+i*0x9A0,(0,1,0x80000000,0xFFFFFFFF)[pattern%4])
        put(memory,FLAGS[1]+i*0x9A0,~pattern&0xFFFFFFFF)
    return memory


def snapshot(memory,view):
    return tuple(int.from_bytes(bytes(memory[a+i] for i in range(n)),'big') for a,n in FIELDS)+tuple(
        read(memory,a+view*0x9A0) for a in FLAGS)


def public(memory):
    return {a:b for a,b in memory.items() if not STACK-0x400<=a<STACK+0x100}


def returned(target,args,ordinal,pattern,gate):
    if target==0x1517EFAC:return (0x80000000 if pattern&1 else 1) if gate==3 else 0
    if target==0x1510B958:return 0xDEADBEEF
    return (args[0]+8*(1+(target//4+ordinal+pattern)%3))&0xFFFFFFFF


def effects(memory,target,args,ordinal,view,mode):
    if mode==1 and target==0x1517EFAC:put(memory,MASK,1<<view,2)
    elif mode==2 and target==0x1517EFAC:put(memory,COUNT,0x7FFFFFFF)
    elif mode==3 and target==0x1510B958:
        put(memory,BASE,0x80507FFC);memory[PAGE]=255
    elif mode==4 and target==0x151135C4 and ordinal==1:memory[MODE]=2
    elif mode==5 and target==0x15035FE8:
        put(memory,STATE,OTHER)
        put(memory,FLAGS[0]+view*0x9A0,read(memory,FLAGS[0]+view*0x9A0)^1)
    elif mode==6 and target==0x1517EFAC:
        put(memory,STATE,OTHER)
    else:return False
    return True


def reference(memory,raw_view=0,pattern=0,gate=0,mode=0,cursor=CURSOR):
    memory,calls,observations,returns,fired=dict(memory),[],[],[],[]
    view=half(raw_view)
    state=(read(memory,STATE)+view*0x9A0)&0xFFFFFFFF
    counts=Counter()
    def call(target,*args):
        args=tuple(a&0xFFFFFFFF for a in args)
        calls.append((target,args));observations.append((target,snapshot(memory,view)))
        counts[target]+=1
        value=returned(target,args,counts[target],pattern,gate)
        returns.append(value)
        if effects(memory,target,args,counts[target],view,mode):fired.append((target,counts[target],mode))
        return value
    def emit(w0,w1):
        nonlocal cursor
        put(memory,cursor,w0);put(memory,cursor+4,w1)
        cursor+=8
    if memory[DISABLED] or int.from_bytes(bytes(memory[STOP+i] for i in range(2)),'big'):
        return memory,calls,observations,returns,fired,cursor
    if call(0x1517EFAC,view) or int.from_bytes(bytes(memory[MASK+i] for i in range(2)),'big')&(1<<view):
        return memory,calls,observations,returns,fired,cursor
    if signed(read(memory,COUNT))>0:
        cursor=call(0x1510B7B4,cursor,view)
        cursor=call(0x1515D6D0,cursor,view)
        call(0x1510B958,view)
        emit(0xDC080008,(read(memory,BASE)+view*0x180+memory[PAGE]*16+64)&0xFFFFFFFF)
        cursor=call(0x1501A490,cursor,view,0,0,0,0)
    cursor=call(0x151135C4,cursor,1,view)
    if memory[MODE]==2:cursor=call(0x151D6778,cursor)
    cursor=call(0x151674F8,cursor,6,view,0)
    cursor=call(0x151674F8,cursor,6,view,1)
    cursor=call(0x15186794,cursor,view)
    cursor=call(0x1501A490,cursor,view,0,0,0,0)
    cursor=call(0x1502BAD0,cursor,1,view)
    cursor=call(0x15035FE8,cursor,view)
    emit(0xDA380003,0x80089470)
    first,last=(0x15018E88,0x15018F08) if read(memory,state+0x5F0)&1 else (0x15018F08,0x15018E88)
    cursor=call(first,cursor,view)
    cursor=call(0x151135C4,cursor,0,view)
    cursor=call(last,cursor,view)
    cursor=call(0x15188D00,cursor,0,view)
    cursor=call(0x15188D00,cursor,1,view)
    cursor=call(0x1502BAD0,cursor,2,view)
    cursor=call(0x151674F8,cursor,2,view,0)
    cursor=call(0x151674F8,cursor,2,view,1)
    return memory,calls,observations,returns,fired,cursor


class RenderOracle(machine.MaskOracle):
    def __init__(self,words,memory,view=0,pattern=0,gate=0,mode=0,phase=0,fault=None,entry=source.ENTRY,arguments=None,connected=None):
        super().__init__(words,memory,phase=phase,fault=None,entry=entry,arguments=arguments or (CURSOR,view),connected=connected)
        self.view,self.pattern,self.gate,self.render_mode=half(view),pattern,gate,mode
        self.current_pc,self.delay_of=entry,None
        self.code=faults.TrackedCode(self.code,self)
        self.root_fault,self.root_accesses=fault,0
        self.root_entry,self.root_size=entry,len(words)*4
        self.counts,self.observations,self.fired=Counter(),[],[]

    def access(self):
        if self.own_instruction and self.root_entry<=self.current_pc<self.root_entry+self.root_size:
            if self.root_accesses==self.root_fault:raise faults.AccessBoundary
            self.root_accesses+=1

    def record_call(self,target):
        args=self.arguments(SIGNATURES[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.observations.append((target,snapshot(self.memory,self.view)))
        self.counts[target]+=1

    def hook(self,target):
        args=self.calls[-1][1]
        value=returned(target,args,self.counts[target],self.pattern,self.gate)
        if effects(self.memory,target,args,self.counts[target],self.view,self.render_mode):
            self.fired.append((target,self.counts[target],self.render_mode))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=value


def state(m):
    return m.memory,m.r,m.f,m.events,m.calls,m.current_pc,m.delay_of,m.root_accesses,m.observations,m.fired
