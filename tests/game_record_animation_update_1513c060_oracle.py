"""Independent integer update model; bounded providers, not hardware exceptions."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,struct
from tools.experiments import game_record_animation_update_1513c060_candidates as c
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as ram

ENTRY,CALLER,RELEASE=0x1513C060,0x151670C0,0x1516972C
RESOURCE,FOLLOW,MARK=0x30000,0x50000,0x60000
UPDATES,EXITS,FRAMES,TICKS=0x80089C70,0x80089CA8,0x80090B64,0x800BE9E4
REGISTRY,HEADS,DEPTH,NEXT=0x8008B4A8,0x800DCE50,0x800DD190,0x800DD198
STACK,u32,rd,wr,signed=ram.STACK,ram.u32,ram.rd,ram.wr,ram.signed
signed16=lambda v:((v&65535)^32768)-32768

class GuestTrap(Exception):
    def __init__(self,code):self.code=code

@dataclass(frozen=True)
class Case:
    enabled:int=1
    flags:int=0
    timer:int=300
    threshold:int=301
    scale:int=1
    alpha:int=255
    animation:int=0
    frames:int=1
    cursor:int=0
    rate:int=1
    ticks:int=1
    update:int=0
    exit:int=0
    answer:int=1
    exit_answer:int=1
    mutation:int=0
    alias:int=0
    seed:int=0
    phase:int=0

def symbols():return dict(D_800BE9E4=TICKS,D_80089C70=UPDATES,D_80089CA8=EXITS,D_80090B64=FRAMES,func_1516972C=RELEASE)
@lru_cache(None)
def retained():
    rom=(c.ROOT/'conker/conker.us.bin').read_bytes()
    return struct.unpack_from('>14I',rom,0x22E730),struct.unpack_from('>4I',rom,0x22E768),rom[0x235624:0x236224]

def base(case):return RESOURCE if case.alias==0 else TICKS-0x20 if case.alias==1 else FRAMES
def fixture(case=Case(),order='big'):
    regions=((RESOURCE,256),(FOLLOW,256),(MARK,16),(FRAMES,3072),(UPDATES,72),(TICKS-32,192),(STACK+case.phase-1024,1536))
    seen=set()
    for a,n in regions:
        addresses={u32(a+i)for i in range(n)};assert not seen&addresses,'Fixture banks must be disjoint';seen|=addresses
    m={u32(a+i):(i*29+case.seed*11+90)&255 for a,n in regions for i in range(n)}
    updates,exits,frames=retained()
    for i,v in enumerate((*updates,*exits)):wr(m,UPDATES+4*i,v,4,order)
    for i,v in enumerate(frames):m[FRAMES+i]=v
    wr(m,TICKS,case.ticks,4,order)
    for p in(base(case),FOLLOW):
        for off,value in((0x10,case.enabled),(0x18,case.flags),(0x20,case.cursor),(0x24,case.rate)):wr(m,p+off,value,4,order)
        for off,value in((0x1C,case.timer),(0x3A,case.threshold),(0x3C,case.scale)):wr(m,p+off,value,2,order)
        for off,value in((0x1E,case.animation),(0x28,case.alpha),(0x2D,91),(0x80,case.update),(0x81,case.exit)):m[p+off]=value&255
    m[FRAMES+(case.animation&255)*12]=case.frames&255
    return m

def public(m,case):return {a:v for a,v in m.items()if not STACK+case.phase-1024<=a<STACK+case.phase+512}
def effect(m,case,t,home,record,order='big'):
    updates,exits,_=retained()
    if t in updates[1:]:
        if case.mutation==1:
            wr(m,record+0x18,0x18000,4,order);wr(m,record+0x1C,-3,2,order);wr(m,record+0x3C,7,2,order);wr(m,TICKS,3,4,order)
        if case.mutation==2:
            assert home is not None;wr(m,home,FOLLOW,4,order);m[home-5]=0x80
        if case.mutation==3:
            wr(m,record+0x20,131071,4,order);wr(m,record+0x24,1,4,order);m[FRAMES+m[record+0x1E]*12]=1
    elif t in exits[1:]:
        if case.mutation==4:
            assert home is not None;wr(m,home,FOLLOW,4,order)
    elif t==RELEASE:wr(m,MARK,record,4,order)

def remainder(a,b):
    assert b!=0
    if a==-2147483648 and b==-1:raise GuestTrap(6)
    q=(abs(a)//abs(b))*(-1 if(a<0)!=(b<0)else 1)
    return a-q*b

def reference(initial,case=Case(),order='big',home=None,record=None):
    m=dict(initial);calls=[];p=base(case)if record is None else record;home=STACK+case.phase if home is None else home;status='return'
    get=lambda off:signed(rd(m,p+off,4,order))
    half=lambda off:signed16(rd(m,p+off,2,order))
    def call(t,record):
        calls.append((t,(u32(record),)));effect(m,case,t,home,record,order)
    if not get(0x10)&1:return dict(memory=m,observed=public(m,case),calls=calls,status=status)
    remove=0
    if get(0x18)&1:
        wr(m,p+0x1C,u32(half(0x1C)-rd(m,TICKS,4,order)),2,order)
        if half(0x1C)<0:remove=1
    index=m[p+0x80]
    if index:
        wr(m,home,p,4,order);m[home-5]=remove&255
        t=rd(m,UPDATES+index*4,4,order);call(t,p);p=rd(m,home,4,order);remove=((m[home-5]^128)-128)
        if u32(case.answer)==0:remove=1
    for flag,off in((0x8000,0x28),(0x10000,0x2D)):
        if get(0x18)&flag and remove==0 and half(0x1C)<half(0x3A):
            v=half(0x1C)*half(0x3C)
            if v<m[p+0x28]:m[p+off]=v&255
    rate=get(0x24)if remove==0 else 0
    if remove==0 and rate!=0:
        limit=(m[FRAMES+m[p+0x1E]*12]<<16)-1
        cursor=signed(u32(get(0x20)+u32(rate)*rd(m,TICKS,4,order)));wr(m,p+0x20,cursor,4,order)
        flags=get(0x18)
        try:
            if cursor>limit:
                if flags&2:remove=1
                elif flags&0x40:wr(m,p+0x24,0,4,order);wr(m,p+0x20,limit,4,order)
                elif flags&4:wr(m,p+0x20,u32(limit-remainder(cursor,limit)),4,order);wr(m,p+0x24,-rate,4,order)
                else:
                    for i in range(32):
                        cursor=signed(u32(cursor-limit));wr(m,p+0x20,cursor,4,order)
                        if cursor<=limit:break
                    else:raise AssertionError('Unbounded positive fixture')
            elif cursor<0:
                if flags&8:remove=1
                elif flags&0x80:wr(m,p+0x24,0,4,order);wr(m,p+0x20,0,4,order)
                elif flags&4:wr(m,p+0x20,remainder(signed(u32(-cursor)),limit),4,order);wr(m,p+0x24,-rate,4,order)
                else:
                    for i in range(32):
                        cursor=signed(u32(cursor+limit));wr(m,p+0x20,cursor,4,order)
                        if cursor>=0:break
                    else:raise AssertionError('Unbounded negative fixture')
        except GuestTrap as e:status=('trap',e.code)
    if status=='return'and remove:
        index=m[p+0x81]
        if index:
            wr(m,home,p,4,order);call(rd(m,EXITS+index*4,4,order),p);p=rd(m,home,4,order)
            if u32(case.exit_answer):call(RELEASE,p)
        else:call(RELEASE,p)
    return dict(memory=m,observed=public(m,case),calls=calls,status=status)

def caller_fixture(case,kind=0x1B,bank=0,chain=1,depth=0):
    m=fixture(case);rom=(c.ROOT/'conker/conker.us.bin').read_bytes()
    for i,v in enumerate(rom[0x22FF68:0x22FF68+101*52]):m[REGISTRY+i]=v
    for i in range(832):m[HEADS+i]=0
    for i in range(32):m[NEXT+i]=(i*11+91)&255
    m[DEPTH]=depth;wr(m,HEADS+bank*416+kind*4,base(case))
    wr(m,base(case)+8,FOLLOW if chain==2 else 0);wr(m,FOLLOW+8,0)
    return m

def caller_reference(initial,case,kind=0x1B,bank=0,chain=1,depth=0):
    m=dict(initial);calls=[];p=base(case);home=STACK+case.phase-64
    m[DEPTH]=depth+1
    while p:
        wr(m,NEXT+4*(depth+1),rd(m,p+8));calls.append((ENTRY,(p,)))
        e=reference(m,case,home=home,record=p);assert e['status']=='return';m=e['memory'];calls.extend(e['calls']);p=rd(m,NEXT+4*(depth+1))
    m[DEPTH]=depth
    return dict(memory=m,observed=public(m,case),calls=calls,status='return')

class Oracle(FactoryOracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,arguments=None):
        self.home=STACK+case.phase;self.status='return'
        super().__init__(words,memory,case,entry=entry,s=symbols(),connected=connected,arguments=arguments or(base(case),))
    def execute(self,w):
        op,fn,rs,rt=w>>26,w&63,w>>21&31,w>>16&31
        if op==0 and fn==13:self.status=('trap',w>>16&1023);raise GuestTrap(w>>16&1023)
        if op==0 and fn==26 and signed(self.r[rs])==-2147483648 and signed(self.r[rt])==-1:
            self.lo,self.hi=0x80000000,0;return
        return super().execute(w)
    def record_call(self,t):
        updates,exits,_=retained();assert t in(*updates[1:],*exits[1:],RELEASE,ENTRY),hex(t)
        a=tuple(map(u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
    def hook(self,t):
        effect(self.memory,self.case,t,self.home,self.calls[-1][1][0]);updates,exits,_=retained();answer=self.case.answer if t in updates[1:]else self.case.exit_answer
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)

state=ram.state

def cases():
    for fade,flags,cursor,rate in itertools.product((0,0x8000,0x10000,0x18000),(0,2,4,8,0x40,0x80,0x42,0x84,0xC0),(-131071,-1,0,65535,65536,131071),(-1,1)):
        yield Case(flags=fade|flags,cursor=u32(cursor),rate=u32(rate),timer=20,scale=2)
    for flags in range(256):yield Case(flags=flags,cursor=65536,rate=1)
    for update,exit,answer,result in itertools.product(range(14),range(4),(0,1),(0,1)):
        yield Case(update=update,exit=exit,answer=answer,exit_answer=result)
    for timer,ticks in itertools.product((-32768,-1,0,32767),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF)):
        yield Case(flags=1,timer=timer,ticks=ticks,rate=0)
    for animation,frames in itertools.product((0,1,29,255),(1,2,255)):
        yield Case(animation=animation,frames=frames,cursor=65536)
    for mutation in range(1,5):yield Case(update=1,exit=1,answer=0 if mutation==4 else 1,mutation=mutation,phase=8)
    for flags,cursor in((2,1),(0x40,1),(4,1),(8,-1),(0x80,-1),(4,-2147483648),(0,2147483647),(0,-2147483648)):
        yield Case(frames=0,flags=flags,cursor=u32(cursor),ticks=0)
    for alias in(1,2):yield Case(alias=alias,cursor=65535,flags=0x18000,timer=20)
    yield Case(flags=0x8001,timer=-1)
    yield Case(flags=0x8000,threshold=300)
    yield Case(flags=0x8000,timer=20,scale=2,alpha=0)
    yield Case(enabled=0)
