"""Sixteen-argument constructor, captured payload and original factory chain."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_owner_vector_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
OWNER,VECTOR,RESULT,ACTOR,MARK=0x30000,0x50000,0x60000,0x70000,0x90000
FACTORY,COPY,ACTOR_FACTORY,CREATE,ALLOCATE,FREE=0x151602C0,0x10022EC0,0x1515D5F8,0x1516037C,0x15167A68,0x1515F10C
RAW=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345)
DEFINED=(0,1,2,3,4,5,*range(8,22))
u32=lambda n:n&0xFFFFFFFF
signed8=lambda n:((n&255)^128)-128
signed16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    index:int=0
    owner:int=OWNER
    vector:int=VECTOR
    outcome:int=2
    mode:int=0
    phase:int=0

def symbols():return dict(func_151602C0=FACTORY,memcpy=COPY)
def args(c):
    i=c.index
    return(c.owner,0xABCD0000|((i*37)&255),c.vector,0xFEED0000|((i*73+255)&255),
        (0x12348000,0x56787FFF,0x7FFFFFFF,0x80000000)[i%4],
        u32(i*1664525+1013904223),u32(~i),0x80000000,0xFFFFFFFF,0xDEAD0009^i,0xBAADF00D^i,
        0x76540000|((i*109+128)&255),(0,0xFFFFFFFF,0x7FFFFFFF,0x80000000)[i%4],
        0xCAFE0000|((i*13+7)&255),0xBEEF0000|((i*53+255)&255),u32(i*1103515245+12345))

def fixture(c=Case(),arguments=None):
    a=args(c)if arguments is None else arguments;home=STACK+c.phase
    m={home+i:(i*17+c.index*13+165)&255 for i in range(-512,1024)}
    for p,n in((OWNER-16,288),(VECTOR-16,64),(RESULT-16,128),(ACTOR-16,96),(MARK,4)):
        m.update({p+i:(i*29+c.index*11+89)&255 for i in range(n)})
    if a[0]and not home-512<=a[0]<home+1024:
        for i in range(128):m.setdefault(a[0]+i,(i*31+89)&255)
    for i in range(3):put(m,OWNER+4*i,0x3F800001+i)
    if a[0]:m[a[0]+0x3B]=c.index&255
    if a[2]:
        for i in range(3):put(m,a[2]+4*i,RAW[(c.index+i*5)%len(RAW)])
    put(m,MARK,0)
    return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+1024}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def effect(m,c,a):
    put(m,MARK,0xC001D00D)
    if c.mode&1:
        m[a[0]+0x3B]^=0x55
        for i in range(3):put(m,a[2]+4*i,read(m,a[2]+4*i)^0xA5A5A5A5)
    if c.mode&2:m[RESULT+8]^=0xA5;m[a[0]+0x3B]^=0xAA

def reference(initial,c=Case(),arguments=None,s=None,home=None,connected=False):
    a=args(c)if arguments is None else arguments;s=symbols()if s is None else s
    home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];copies=[];snapshots=[]
    if not a[0]:return m,calls,0,copies,snapshots
    header,zero,payload=home-12,home-48,home-36
    m[header]=a[3]&255;m[header+1]=5;m[header+4]=16;put(m,header+2,a[4]&65535,2)
    put(m,payload,a[0]);m[payload+4]=m[a[0]+0x3B];m[payload+5]=a[1]&255
    for i in range(12):m[payload+8+i]=m[a[2]+i]
    for i in range(3):put(m,zero+4*i,0)
    m[payload+20]=a[11]&255;m[payload+21]=a[13]&255
    size=u32(a[12]+24);factory=(header,zero,*a[5:9],255,0,size,a[14]&255,u32(a[15]))
    calls.append((s['func_151602C0'],factory));snapshots.append((data(m,header,6),data(m,zero,12),data(m,payload,24)))
    effect(m,c,a)
    def copy(dst,src,n):
        calls.append((s['memcpy'],(dst,src,n)));blob=data(m,src,n);copies.append((dst,blob,n))
        for i,value in enumerate(blob):m[dst+i]=value
    result=RESULT if c.outcome==2 else 0
    if connected:
        calls.append((ACTOR_FACTORY,(0,0,0,*a[5:9],255,0,0)))
        if c.outcome:
            calls.append((CREATE,(header,ACTOR,size,a[14]&255,u32(a[15]))))
            calls.append((ALLOCATE,(53,u32(a[15]),u32(size+24),1,a[14]&255,1)))
            if result:
                copy(RESULT+14,header,6);put(m,RESULT+20,ACTOR);m[RESULT+14]|=2
            else:calls.append((FREE,(ACTOR,)))
    elif result:
        for i in range(6):m[RESULT+14+i]=m[header+i]
        put(m,RESULT+20,ACTOR);m[RESULT+14]|=2
    if result:copy(RESULT+24,payload,24)
    return m,calls,result,copies,snapshots

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),arguments=None,s=None,entry=source.ENTRY,connected=None):
        self.c=c;self.a=args(c)if arguments is None else tuple(arguments);self.s=symbols()if s is None else s
        self.snapshots=[];self.effect_fired=False
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=self.a)
        self.before_f=self.f[:]
    def record_call(self,t):
        counts={source.ENTRY:16,self.s['func_151602C0']:11,self.s['memcpy']:3,ACTOR_FACTORY:10,CREATE:5,ALLOCATE:6,FREE:1}
        assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==source.ENTRY:self.a=a;self.target_home=self.r[29]
        if t==self.s['func_151602C0']:
            self.snapshots.append((data(self.memory,a[0],6),data(self.memory,a[1],12),data(self.memory,self.target_home-36,24)))
        if t==self.s['memcpy']:self.copy_observations.append((a[0],data(self.memory,a[1],a[2]),a[2]))
    def hook(self,t):
        a=self.calls[-1][1];result=0xDEADBEEF
        if t in(self.s['func_151602C0'],ACTOR_FACTORY):
            assert not self.effect_fired;effect(self.memory,self.c,self.a);self.effect_fired=True
            if t==ACTOR_FACTORY:result=ACTOR if self.c.outcome else 0
            else:
                result=RESULT if self.c.outcome==2 else 0
                if result:
                    for i in range(6):self.memory[RESULT+14+i]=self.memory[a[0]+i]
                    put(self.memory,RESULT+20,ACTOR);self.memory[RESULT+14]|=2
        elif t==ALLOCATE:result=RESULT if self.c.outcome==2 else 0
        elif t==FREE:assert a==(ACTOR,)
        else:
            assert t==self.s['memcpy']and a[2]in(6,24)
            blob=data(self.memory,a[1],a[2])
            for i,v in enumerate(blob):self.memory[a[0]+i]=v
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)

def payload(obj):
    t,fs,rs=parse_object(obj);f=fs[source.FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:v for p,v in rs.items()if a<=p<a+n}
def bound(obj,s=None):return bound_blob(*payload(obj),symbols()if s is None else s)
def cases():
    for i,outcome,mode,phase in itertools.product(range(256),(0,1,2),(0,3),(0,8)):
        yield Case(i,outcome=outcome,mode=mode,phase=phase)
    for i,outcome,phase in itertools.product((0,127,128,255),(0,2),(0,8)):
        yield Case(i,owner=0,vector=0,outcome=outcome,phase=phase)
def controls():
    b=source.SELECTED
    return dict(wrong_owner_gate=b.replace('if (owner == 0)','if (owner == 0 || (kind & 1))'),
        wrong_identity=b.replace('owner[0x3B]','owner[0x3A]'),
        wrong_kind=b.replace('payload.kind = kind;','payload.kind = headerId;'),
        wrong_lifetime=b.replace('header.unk2 = lifetime;','header.unk2 = 0;'),
        wrong_vector=b.replace('payload.vector = *(struct17 *)vector;','payload.vector = *(struct17 *)owner;'),
        shifted_tag=b.replace('payload.tag = payloadTag;','payload.tag = (s8)unused10;'),
        wrong_size=b.replace('+ sizeof(payload)', '+ sizeof(payload) - 1u'),
        wrong_failure_return=b.replace('return result;','return result != 0 ? result : (struct225 *)owner;'),
        short_copy=b.replace('&payload, sizeof(payload)','&payload, sizeof(payload) - 1u'),
        false_return=b.replace('return result;','return 0;'))

# Complete argument-setup windows. Prior unrelated calls/branches are explicit
# entry preconditions; the setup and the authentic constructor JAL execute.
CALLER_ENTRIES=(0x150F0938,0x150F09A8,0x150FA128,0x1514D8F8,0x1514DBB8,0x1514DF50,
                0x1514E47C,0x1514EECC,0x1514F20C,0x1514F278,0x15163C2C,0x151A347C)
CALLER_PCS=(0x150F09A0,0x150F0A0C,0x150FA184,0x1514D950,0x1514DC20,0x1514DFA8,
            0x1514E4F0,0x1514EF34,0x1514F270,0x1514F2D8,0x15163C94,0x151A34E8)
def expected_caller(index,owner,home,priority,user):
    table=(
        (owner,37,0x800A1674,2,300,4,0,255,0,255,0,-1,0,0,255,1),
        (owner,2,0x800A1680,2,300,13,255,255,255,255,0,-1,0,0,255,1),
        (owner,1,0x800A1CC0,3,70,40,255,255,255,255,0,-1,0,0,0x12340000|priority,user),
        (owner,5,home+0x54,2,300,40,255,0,0,255,0,1,0,0,255,1),
        (owner,2,0x800A58A0,2,300,40,255,255,255,255,0,-1,0,0,255,1),
        (owner,0,0x800A58C4,2,300,11,255,255,255,2,0,-1,0,0,255,1),
        (owner,12,home+0x50,2,300,40,255,181,0,255,0,2,0,0,255,1),
        (owner,1,0x800A5934,2,300,2,255,0,0,255,0,3,0,0,255,1),
        (owner,1,0x800A5958,2,300,12,255,255,255,2,0,-1,0,0,255,1),
        (owner,1,0x800A5964,2,300,15,255,0,0,255,1,-1,0,0,255,1),
        (owner,1,0x800A6A0C,2,300,100,0,255,0,255,0,0,16,1,priority,user),
        (owner,1,home+0x5C,2,300,80,255,255,117,255,0,-1,0,0,priority,1))
    return tuple(map(u32,table[index]))

def caller_fixture(index,c):
    initial=fixture(c);sp=STACK+c.phase
    for at in(0x48,0x60,0x120,0x130):put(initial,sp+at,c.owner)
    initial[sp+0x67]=c.index&255;initial[sp+0x9F]=c.index&255;put(initial,sp+0x68,0x87654321)
    for p in(0x800A1674,0x800A1680,0x800A1CC0,0x800A58A0,0x800A58C4,0x800A5934,0x800A5958,0x800A5964,0x800A6A0C):
        for i in range(3):put(initial,p+4*i,RAW[(c.index+i*3)%len(RAW)])
    return initial

class CallerOracle(Oracle):
    def record_call(self,t):
        super().record_call(t)
        if t==source.ENTRY:
            self.entry_contract=reference(self.memory,self.c,self.a,self.s,self.r[29])

def caller_machine(rom,words,index,c):
    from tools.tests.test_game_character_effect_pair import WindowCode
    start,pc=CALLER_ENTRIES[index],CALLER_PCS[index];end=pc+8;offset=start-0x15000000+0x2D4B0
    body=struct.unpack_from('>%dI'%((end-start)//4),rom,offset)
    code=dict(zip(range(source.ENTRY,source.ENTRY+284,4),words));code[end]=0
    m=CallerOracle(body,caller_fixture(index,c),c,entry=start,connected=code)
    m.r[16]=m.r[22]=c.owner;m.r[20]=0x12340000|(c.index&255);m.r[21]=0x87654321
    if index==5:m.r[5]=0;m.r[6]=0x800A58C4
    m.f[10]=0x3FA00000;m.f[16]=0xBF000000;m.f[20]=0
    m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    return m
