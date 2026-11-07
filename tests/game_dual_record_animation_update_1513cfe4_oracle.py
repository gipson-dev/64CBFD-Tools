"""Independent integer update model; bounded providers, not hardware exceptions."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,struct
from tools.experiments import game_dual_record_animation_update_1513cfe4_candidates as c
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as ram

ENTRY,CALLER,RELEASE=0x1513CFE4,0x151670C0,0x1516972C
RESOURCE,FOLLOW,MARK=0x30000,0x50000,0x60000
UPDATES,SECOND,EXITS,FRAMES,TICKS=0x80089CB8,0x80089D60,0x80089E10,0x80090B64,0x800BE9E4
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
    second:int=0
    second_answer:int=1
    exit:int=0
    answer:int=1
    exit_answer:int=1
    mutation:int=0
    alias:int=0
    seed:int=0
    phase:int=0

def symbols():return dict(D_800BE9E4=TICKS,D_80089CB8=UPDATES,D_80089D60=SECOND,D_80089E10=EXITS,D_80090B64=FRAMES,func_1516972C=RELEASE)
@lru_cache(None)
def retained():
    rom=(c.ROOT/'conker/conker.us.bin').read_bytes()
    return struct.unpack_from('>42I',rom,0x22E778),struct.unpack_from('>44I',rom,0x22E820),struct.unpack_from('>3I',rom,0x22E8D0),rom[0x235624:0x236224]

def base(case):return RESOURCE if case.alias==0 else TICKS-0x20 if case.alias==1 else FRAMES
def fixture(case=Case(),order='big'):
    regions=((RESOURCE,256),(FOLLOW,256),(MARK,16),(FRAMES,3072),(UPDATES,356),(TICKS-32,192),(STACK+case.phase-1024,1536))
    seen=set()
    for a,n in regions:
        addresses={u32(a+i)for i in range(n)};assert not seen&addresses,'Fixture banks must be disjoint';seen|=addresses
    m={u32(a+i):(i*29+case.seed*11+90)&255 for a,n in regions for i in range(n)}
    updates,second,exits,frames=retained()
    for i,v in enumerate((*updates,*second,*exits)):wr(m,UPDATES+4*i,v,4,order)
    for i,v in enumerate(frames):m[FRAMES+i]=v
    wr(m,TICKS,case.ticks,4,order)
    for p in(base(case),FOLLOW):
        for off,value in((0x10,case.enabled),(0x58,case.flags),(0x20,case.cursor),(0x24,case.rate)):wr(m,p+off,value,4,order)
        for off,value in((0x1C,case.timer),(0x6C,case.threshold),(0x6E,case.scale)):wr(m,p+off,value,2,order)
        for off,value in((0x18,case.animation),(0x5C,case.alpha),(0x2B,91),(0x70,case.update),(0x71,case.second),(0x72,case.exit)):m[p+off]=value&255
    m[FRAMES+(case.animation&255)*12]=case.frames&255
    return m

def public(m,case):return {a:v for a,v in m.items()if not STACK+case.phase-1024<=a<STACK+case.phase+512}
def effect(m,case,stage,home,record,order='big'):
    if stage in(0,1):
        if case.mutation==1:
            wr(m,record+0x58,0x18000000,4,order);wr(m,record+0x1C,-3,2,order);wr(m,record+0x6E,7,2,order);wr(m,TICKS,3,4,order)
        if case.mutation==2:
            assert home is not None;wr(m,home,FOLLOW,4,order);m[home-5]=0x80
        if case.mutation==3:
            wr(m,record+0x20,131071,4,order);wr(m,record+0x24,1,4,order);m[FRAMES+m[record+0x18]*12]=1
        if case.mutation==5 and stage==0:m[record+0x71]=2;m[record+0x72]=2
        if case.mutation==6 and stage==1:wr(m,record+0x58,0x18000000,4,order)
    elif stage==2:
        if case.mutation==4:
            assert home is not None;wr(m,home,FOLLOW,4,order)
    elif stage==3:wr(m,MARK,record,4,order)

def remainder(a,b):
    assert b!=0
    if a==-2147483648 and b==-1:raise GuestTrap(6)
    q=(abs(a)//abs(b))*(-1 if(a<0)!=(b<0)else 1)
    return a-q*b

def reference(initial,case=Case(),order='big',home=None,record=None):
    m=dict(initial);calls=[];p=base(case)if record is None else record;home=STACK+case.phase if home is None else home;status='return'
    get=lambda off:signed(rd(m,p+off,4,order))
    half=lambda off:signed16(rd(m,p+off,2,order))
    def call(t,record,stage):
        calls.append((t,(u32(record),)));effect(m,case,stage,home,record,order)
    if not get(0x10)&1:return dict(memory=m,observed=public(m,case),calls=calls,status=status)
    remove=0
    if get(0x58)&1:
        wr(m,p+0x1C,u32(half(0x1C)-rd(m,TICKS,4,order)),2,order)
        if half(0x1C)<0:remove=1
    # Both services run, and each reloads its selector/resource after the prior call.
    for stage,table,offset,answer in((0,UPDATES,0x70,case.answer),(1,SECOND,0x71,case.second_answer)):
        index=m[p+offset]
        if index:
            wr(m,home,p,4,order);m[home-5]=remove&255
            call(rd(m,table+index*4,4,order),p,stage);p=rd(m,home,4,order);remove=((m[home-5]^128)-128)
            if u32(answer)==0:remove=1
    for flag,off in((0x08000000,0x5C),(0x10000000,0x2B)):
        if get(0x58)&flag and remove==0 and half(0x1C)<half(0x6C):
            v=half(0x1C)*half(0x6E)
            if v<m[p+0x5C]:m[p+off]=v&255
    rate=get(0x24)if remove==0 else 0
    if remove==0 and rate!=0:
        limit=(m[FRAMES+m[p+0x18]*12]<<16)-1
        cursor=signed(u32(get(0x20)+u32(rate)*rd(m,TICKS,4,order)));wr(m,p+0x20,cursor,4,order)
        flags=get(0x58)
        try:
            if cursor>limit:
                if flags&0x800:remove=1
                elif flags&0x400:wr(m,p+0x20,u32(limit-remainder(cursor,limit)),4,order);wr(m,p+0x24,-rate,4,order)
                else:
                    for i in range(32):
                        cursor=signed(u32(cursor-limit));wr(m,p+0x20,cursor,4,order)
                        if cursor<=limit:break
                    else:raise AssertionError('Unbounded positive fixture')
            elif cursor<0:
                if flags&0x1000:remove=1
                elif flags&0x400:wr(m,p+0x20,remainder(signed(u32(-cursor)),limit),4,order);wr(m,p+0x24,-rate,4,order)
                else:
                    for i in range(32):
                        cursor=signed(u32(cursor+limit));wr(m,p+0x20,cursor,4,order)
                        if cursor>=0:break
                    else:raise AssertionError('Unbounded negative fixture')
        except GuestTrap as e:status=('trap',e.code)
    if status=='return'and remove:
        index=m[p+0x72]
        if index:
            wr(m,home,p,4,order);m[home-5]=remove&255
            call(rd(m,EXITS+index*4,4,order),p,2);p=rd(m,home,4,order);remove=((m[home-5]^128)-128)
            if u32(case.exit_answer):remove=0
        if remove:call(RELEASE,p,3)
    return dict(memory=m,observed=public(m,case),calls=calls,status=status)

def caller_fixture(case,kind=0x1C,bank=0,chain=1,depth=0):
    m=fixture(case);rom=(c.ROOT/'conker/conker.us.bin').read_bytes()
    for i,v in enumerate(rom[0x22FF68:0x22FF68+101*52]):m[REGISTRY+i]=v
    for i in range(832):m[HEADS+i]=0
    for i in range(32):m[NEXT+i]=(i*11+91)&255
    m[DEPTH]=depth;wr(m,HEADS+bank*416+kind*4,base(case))
    wr(m,base(case)+8,FOLLOW if chain==2 else 0);wr(m,FOLLOW+8,0)
    return m

def caller_reference(initial,case,kind=0x1C,bank=0,chain=1,depth=0):
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
        updates,second,exits,_=retained();assert t in(*updates[1:],*second[1:],*exits[1:],RELEASE,ENTRY),hex(t)
        a=tuple(map(u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
    def hook(self,t):
        # One target occurs in both tables; call site, not address, defines stage.
        stage=3 if t==RELEASE else {0x1513D060:0,0x1513D098:1,0x1513D2C0:2}[self.r[31]]
        effect(self.memory,self.case,stage,self.home,self.calls[-1][1][0]);answer=(self.case.answer,self.case.second_answer,self.case.exit_answer,0)[stage]
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)

state=ram.state

def cases():
    for fade,flags,cursor,rate in itertools.product((0,0x08000000,0x10000000,0x18000000),(0,0x400,0x800,0x1000,0xC00,0x1400),(-131071,-1,0,65535,65536,131071),(-1,1)):
        yield Case(flags=fade|flags,cursor=u32(cursor),rate=u32(rate),timer=20,scale=2)
    # Each retained nonzero selector and all independent callback results.
    for table,n in(('update',42),('second',44),('exit',3)):
        for index,answer in itertools.product(range(n),(0,1)):
            args=dict(update=1,second=1,exit=1,answer=answer,second_answer=answer,exit_answer=answer);args[table]=index
            yield Case(**args)
    for first,second,exit,a,b,e in itertools.product((0,1,19),(0,1,29),(0,1,2),(0,1),(0,1),(0,1)):
        yield Case(update=first,second=second,exit=exit,answer=a,second_answer=b,exit_answer=e)
    for timer,ticks in itertools.product((-32768,-1,0,32767),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF)):
        yield Case(flags=1,timer=timer,ticks=ticks,rate=0)
    for animation,frames in itertools.product((0,1,29,255),(1,2,255)):
        yield Case(animation=animation,frames=frames,cursor=65536)
    for mutation in range(1,7):yield Case(update=1,second=1,exit=1,answer=0 if mutation==4 else 1,second_answer=0 if mutation==4 else 1,exit_answer=0,mutation=mutation,phase=8)
    for flags,cursor in((0x800,1),(0x400,1),(0x1000,-1),(0x400,-2147483648),(0,2147483647),(0,-2147483648)):
        yield Case(frames=0,flags=flags,cursor=u32(cursor),ticks=0)
    for alias in(1,2):yield Case(alias=alias,cursor=65535,flags=0x18000000,timer=20)
    yield Case(flags=0x08000001,timer=-1)
    yield Case(flags=0x08000000,threshold=300)
    yield Case(flags=0x08000000,timer=20,scale=2,alpha=0)
    yield Case(enabled=0)
