"""Independent dispatcher model with aliased state, bounded providers and guest access cuts."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,struct,time
from contextlib import contextmanager
from tools.tests import game_record_cleanup_oracle as cleanup
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

ENTRY=0x15183D28
RESOURCE,FREE,DISABLED,AFTER1,AFTER2=0x1510D630,0x10004074,0x800BEAC0,0x151670C0,0x15177A94
TABLE,FLAGS,VIEWS,TIMERS,TICKS,GEOMETRY,SECOND,INDICES,COUNTS=0x800DDE80,0x800DDF68,0x800DDF78,0x800DDF60,0x800BE9E4,0x8008D0B0,0x8008D318,0x8008D3C0,0x800A72E8
UPDATE,SPECIAL7,SPECIAL89,CLEANUP=0x15165C80,0x1517725C,0x15179DB0,0x15183C28
u32=lambda x:x&0xFFFFFFFF
s32=lambda x:(x&0x7FFFFFFF)-(x&0x80000000)
s8=lambda x:(x&127)-(x&128)
public=lambda m:{a:v for a,v in m.items()if not STACK-2048<=a<STACK+768}

@dataclass(frozen=True)
class Case:
    seed:int=0
    pattern:int=0
    mode:int=0
    ticks:int=1
    slot:int=-1
    flag:int=1
    phase:int=0

def fixture(c):
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,768)}
    for base,n in ((TABLE,0x140),(GEOMETRY,0x33C),(COUNTS,16),(TICKS,4)):
        m.update({base+i:(i*29+c.seed+0xA5)&255 for i in range(n)})
    for i in range(11):
        put(m,TABLE+20*i,0 if c.pattern&1 and (i+c.seed)%3==0 else 0x70000+i*0x100)
        put(m,TABLE+20*i+4,0x80000+i*0x100);put(m,TABLE+20*i+8,0x90000+i*0x100)
        put(m,TABLE+20*i+12,0xA0000+i*0x100);put(m,TABLE+20*i+16,0xB0000+i*0x100)
        put(m,VIEWS+4*i,0 if c.pattern&2 and (i+c.seed)%4==0 else 0xC0000+4*i)
        m[FLAGS+i]=((1,0,255,254,128,127)[(i+c.seed)%6]if c.pattern&4 else c.flag)&255
        put(m,INDICES+4*i,0xD0000+i*32);m[COUNTS+i]=(i*47+c.seed)&255
    for i in range(14):
        for j,offset in enumerate((24,28,32,36,40,44,48)):
            put(m,GEOMETRY+56*i+offset,(0,0x80000000,0x3F800000,0x7F800000,0x7FC12345,0xFF800000,0xBF000000)[(i+j+c.seed)%7])
    for i in range(4):m[TIMERS+i]=((0,1,2,255)[(i+c.seed)%4]if c.pattern&8 else(c.seed+i*61)&255)
    if c.slot>=0:m[FLAGS+c.slot]=c.flag&255
    put(m,TICKS,u32(c.ticks));return m

def effect(m,c,target,args,ordinal):
    if c.mode==1:m[FLAGS+(ordinal+3)%11]=1
    elif c.mode==2:m[FLAGS+7]=254
    elif c.mode==3:
        m[FLAGS+7]=1;put(m,TABLE+7*20,0x77000);put(m,VIEWS+7*4,0xCC007)
    elif c.mode==4:put(m,TABLE+20*((ordinal+4)%11),0)
    elif c.mode==5:
        for offset in (36,40,44,48):put(m,GEOMETRY+56*((ordinal+2)%14)+offset,0x3E800000+ordinal)
    elif c.mode==6 and target==CLEANUP:
        m[FLAGS+8]=m[FLAGS+9]=254;put(m,TABLE+9*20,0x79000);put(m,VIEWS+9*4,0xCC009)
    elif c.mode==7:
        m[FLAGS+(ordinal+5)%11]=255;put(m,VIEWS+4*((ordinal+6)%11),0);put(m,TICKS,0xDEADBEEF)

def reference(initial,c,connected_cleanup=False):
    m=dict(initial);calls=[];ordinal=0
    def call(target,*args):
        nonlocal ordinal
        args=tuple(map(u32,args));calls.append((target,args));ordinal+=1
        if connected_cleanup and target==CLEANUP:
            copied,extra=cleanup.reference(m,cleanup.Case(index=args[0],resource_mode=7 if c.mode&1 else 0,free_mode=3 if c.mode&2 else 0));m.clear();m.update(copied);calls.extend(extra)
        else:effect(m,c,target,args,ordinal)
    for i in range(11):
        if s8(m[FLAGS+i])>=-1 and (not read(m,TABLE+20*i)or not read(m,VIEWS+4*i)):m[FLAGS+i]=254
    for i in range(4):
        n=m[TIMERS+i]
        if n:
            remaining=s32(u32(n-read(m,TICKS)));m[TIMERS+i]=max(remaining,0)&255
    for indices,base,word,bias in ((range(7),GEOMETRY,8,0),(range(2,5),SECOND,4,2)):
        for i in indices:
            if m[FLAGS+i]==1:
                p=base+(i-bias)*56
                call(UPDATE,p+24,read(m,TABLE+i*20+word),read(m,p+48),p+36,read(m,p+40),read(m,p+44),read(m,INDICES+4*i),m[COUNTS+i])
    if m[FLAGS+7]==1:call(SPECIAL7,7)
    for i in (8,9):
        if m[FLAGS+i]==1:call(SPECIAL89,i)
    if m[FLAGS+7]==1:m[FLAGS+10]=1
    for i in range(11):
        if m[FLAGS+i]==254 and read(m,TABLE+20*i):call(CLEANUP,i)
    for i in range(11):
        value=s8(m[FLAGS+i])
        if value>0:m[FLAGS+i]=0
        elif value in (0,-1):m[FLAGS+i]=(value-1)&255
    return m,calls

class DispatchOracle(TimingOracle):
    def __init__(self,words,memory,c,entry=None,connected=None):
        self.case=c;self.ordinal=0;self.cleanup_index=0
        super().__init__(words,memory,phase=c.phase,entry=ENTRY if entry is None else entry,connected=connected,arguments=(0x12345678,0xFEDCBA98,0x87654321,0xA5A5A5A5))
        self.trace=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def execute(self,word):
        if word>>26==0x20:
            self.own_instruction=True
            try:
                rs,rt=word>>21&31,word>>16&31;imm=word&65535;value=self.get(u32(self.r[rs]+(imm if imm<32768 else imm-65536)),1);self.r[rt]=u32(s8(value));self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)
    def record_call(self,target):
        assert target in (ENTRY,UPDATE,SPECIAL7,SPECIAL89,CLEANUP,RESOURCE,FREE,AFTER1,AFTER2),hex(target)
        args=self.arguments(8 if target==UPDATE else 0 if target in(ENTRY,AFTER1,AFTER2)else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target in(UPDATE,SPECIAL7,SPECIAL89,CLEANUP):self.ordinal+=1
        if target==CLEANUP:self.cleanup_index=args[0]
    def hook(self,target):
        if target in(RESOURCE,FREE):
            c=cleanup.Case(index=self.cleanup_index,resource_mode=7 if self.case.mode&1 else 0,free_mode=3 if self.case.mode&2 else 0)
            (cleanup.resource_effect if target==RESOURCE else cleanup.free_effect)(self.memory,c,cleanup.symbols())
        elif target==AFTER1:self.memory[DISABLED]=self.case.mode&1
        elif target==AFTER2:pass
        else:effect(self.memory,self.case,target,self.calls[-1][1],self.ordinal)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.lo,self.hi=0xA5000010,0xA5000011

def corpus():
    for pattern,mode,flag in itertools.product(range(16),range(8),(1,0,255,254)):
        yield Case(seed=pattern*7+mode,pattern=pattern,mode=mode,flag=flag,ticks=(0,1,2,255,256,-1,-255,0x7FFFFFFF)[mode],phase=(mode%2)*8)
    for slot,flag in itertools.product(range(11),range(256)):
        yield Case(seed=flag,slot=slot,flag=flag,pattern=12,mode=flag%8,ticks=(0,1,255,256,-1)[flag%5],phase=(flag%2)*8)
    for ticks in (0x80000000,0x80000001,0x7FFFFFFF,0xFFFFFFFF):yield Case(ticks=ticks,flag=1,pattern=8)

SYMBOL_ROLES=dict(D_800DDE80='TABLE',D_800DDF68='FLAGS',D_800DDF78='VIEWS',D_800DDF60='TIMERS',D_800BE9E4='TICKS',D_8008D0B0='GEOMETRY',D_8008D318='SECOND',D_8008D3C0='INDICES',D_800A72E8='COUNTS',func_15165C80='UPDATE',func_1517725C='SPECIAL7',func_15179DB0='SPECIAL89',func_15183C28='CLEANUP')
def symbols():return {name:globals()[role]for name,role in SYMBOL_ROLES.items()}|{'D_800DDF64':TIMERS+4,'D_800DDF73':FLAGS+11}
@contextmanager
def layout(entry,s):
    old={role:globals()[role]for role in SYMBOL_ROLES.values()};old['ENTRY']=ENTRY
    try:
        globals().update({role:s[name]for name,role in SYMBOL_ROLES.items()});globals()['ENTRY']=entry
        yield
    finally:globals().update(old)
