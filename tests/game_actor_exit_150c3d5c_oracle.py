"""Private callback contracts, real seed decoder and original record constructor."""
from dataclasses import dataclass
from collections import Counter
from functools import lru_cache
import hashlib,json,math,struct
from tools.experiments import game_actor_exit_150c3d5c_recovery as s
from tools.experiments import game_type07_parameter_record_match as factory
from tools.tests.game_actor_motion_150c3574_qualification import Oracle as BaseOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK

OWNER,OUTPUT,MARK,PATCH,COEFF=0x30040,0x50040,0x70000,0x10004074,0x800A0338
FACTORY,ALLOC,DECODE,READ,DEBRIS,SPRAY,CONFIG,RANDOM,EMIT=(
    0x151B9BF0,0x15167A68,0x150C3D48,0x151EF040,0x15171200,
    0x151709B4,0x1516D99C,0x150ADA20,0x151602C0)
PARENT_AUDIO,PARENT_STATE=0x10010630,0x15060F28
CONFIG_VALUES=(13,0,0,0,0,0,0,0,0,4,0,0,0,255,0,0,0,20,20,2,0,0,0,0,
    81,81,81,81,10,1,0,255,10,1400,400,1,1,0,1,0,0,0,0,0,255,0)
assert len(CONFIG_VALUES)==46
signed16=lambda n:((n&65535)^32768)-32768
u32=lambda n:n&0xFFFFFFFF

@dataclass(frozen=True)
class Case:
    seed:int=0
    phase:int=0
    read_mode:int=0
    mutation:int=0
    outcome:int=1

def cases():
    for i in range(512):yield Case(i,i%2*8,i//2%3,i%2,i//6%2)

@lru_cache(maxsize=1)
def rom():return (s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2048)}
    for base,n in ((OWNER-32,128),(OUTPUT-32,128),(MARK,4),(PATCH,8),(COEFF,4)):
        m.update({base+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
    coords=(-65536.5,-32768.75,0.,32767.75,65536.5)
    for off,v in ((0x14,coords[c.seed%5]),(0x18,coords[c.seed//5%5]),(0x1C,coords[c.seed//25%5])):put(m,OWNER+off,bits(v))
    for i,b in enumerate(rom()[0x4074:0x407C]):m[PATCH+i]=b
    put(m,MARK,0);put(m,COEFF,0xBF333333)
    return m

def public(m):return {p:v for p,v in m.items() if not STACK-2048<=p<STACK+2048}
def coords(m):return tuple(read(m,OWNER+i) for i in (0x14,0x18,0x1C))
def integers(m):return tuple(math.trunc(floating(v)) for v in coords(m))
def draw(c,n):return (0,0xFFFFFFFF,0x80000000,10,11,51,52)[(c.seed//12+n)%7]

def effect(m,c,t,n):
    put(m,MARK,u32(0x13579BDF+t+n*0x10203))
    if not c.mutation:return
    values={ALLOC:(1.25,2.5,3.75),READ:(4.5,-6.75,8.25),DEBRIS:(17.25,-31.5,103.75),
            SPRAY:(65537.75,-32769.5,32768.25),CONFIG:(75.5,-95.75,144.125)}
    if t==RANDOM:values[t]=(9.5,-20.25,25.75) if n==0 else (-999.25,444.25,777.5)
    if t in values:
        for off,v in zip((0x14,0x18,0x1C),values[t]):put(m,OWNER+off,bits(v))

def reference(initial,c):
    m=dict(initial);calls=[];counts=Counter();observations=[]
    def call(t,*args):
        calls.append((t,tuple(map(u32,args))));n=counts[t];counts[t]+=1;effect(m,c,t,n)
        return draw(c,n) if t==RANDOM else 0xD00D0000
    xyz=tuple(signed16(v) for v in integers(m));args=(47,1,*xyz,1400,1280,800,1200,512,512,30,1,0,255,0)
    calls.append((FACTORY,tuple(map(u32,args))));call(ALLOC,7,0,44,0,255,1)
    if c.outcome:
        for i in range(44):m[OUTPUT+i]=(i*19+c.seed*7+0x31)&255
        put(m,OUTPUT+16,0);m[OUTPUT+20]=47;m[OUTPUT+21]=1
        for i,v in enumerate(args[2:13]):put(m,OUTPUT+22+2*i,v,2)
    calls.append((DECODE,(0xC23459B8,)))
    call(READ,0xB0000340,0)
    word=(0x0330C820,0x0330C821,0xC23459B8)[c.read_mode]
    if word!=0x0330C820:put(m,PATCH,0x03E00008);put(m,PATCH+4,0)
    x,y,z=coords(m)
    call(DEBRIS,3,203,x,y,z,bits(10.),bits(1.),bits(2.),bits(60.),3,60,read(m,COEFF),255,0)
    x,y,z=coords(m);call(SPRAY,math.trunc(floating(x)),math.trunc(floating(bits(floating(y)+20.))),math.trunc(floating(z)),10,bits(2000.),255,0)
    call(CONFIG,*(signed16(v) for v in integers(m)),*CONFIG_VALUES)
    duration=call(RANDOM)%11+10
    snapshot=tuple(map(u32,integers(m)))
    life=call(RANDOM)%52+40
    observations.append(((3,255,duration,0),snapshot))
    call(EMIT,0,0,life,255,255,90,255,0,0,255,1)
    return public(m),calls,observations

@lru_cache(maxsize=1)
def helper_code():
    raw=rom()[factory.ROM:factory.ROM+192];assert hashlib.sha256(raw).hexdigest()==factory.TRUTH_SHA
    code=dict(zip(range(FACTORY,FACTORY+192,4),struct.unpack('>48I',raw)))
    raw=rom()[0xF11F8:0xF120C];assert len(raw)==20
    code.update(zip(range(DECODE,DECODE+20,4),struct.unpack('>5I',raw)))
    return code

class Oracle(BaseOracle):
    def __init__(self,words,initial,c,entry=s.ENTRY,connected=None):
        code=dict(helper_code());code.update(connected or {})
        super().__init__(words,initial,c,entry=entry,connected=code)
        self.counts=Counter();self.observed=[];self.entries=[]
    def record_call(self,t):
        if t==s.ENTRY:self.entries.append(self.r[4]);return
        if t==FACTORY:
            a=list(self.arguments(16));a[2:13]=[u32(signed16(v)) for v in a[2:13]];a[14]&=255;a=tuple(a)
        elif t==DECODE:a=(self.r[4],)
        elif t==READ:
            pointer=self.r[5];assert read(self.memory,pointer)==0xC23459B8
            assert STACK+self.case.phase-256<=pointer<=STACK+self.case.phase-4
            a=(self.r[4],0)
        elif t==EMIT:
            a=list(self.arguments(11));p,q=a[:2]
            assert self.r[29]<=p and p+6<=STACK+self.case.phase and self.r[29]<=q and q+12<=STACK+self.case.phase
            self.observed.append(((self.memory[p],self.memory[p+1],read(self.memory,p+2,2),self.memory[p+4]),tuple(read(self.memory,q+4*i) for i in range(3))))
            a=tuple((0,0,*a[2:]))
        elif t in (ALLOC,DEBRIS,SPRAY,CONFIG,PARENT_AUDIO,PARENT_STATE):a=tuple(self.arguments({ALLOC:6,DEBRIS:14,SPRAY:7,CONFIG:49,PARENT_AUDIO:5,PARENT_STATE:2}[t]))
        elif t==RANDOM:a=()
        else:raise AssertionError(hex(t))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t not in (FACTORY,DECODE),'Original helper code must execute'
        n=self.counts[t];self.counts[t]+=1
        pointer=self.r[5] if t==READ else None
        effect(self.memory,self.case,t,n);answer=0xD00D0000
        if t==READ:
            if self.case.read_mode!=2:put(self.memory,pointer,(0x0330C820,0x0330C821)[self.case.read_mode])
            answer=0xFFFFFFFF if self.case.read_mode==2 else 0
        elif t==ALLOC:
            answer=OUTPUT if self.case.outcome else 0
            if answer:
                for i in range(44):self.memory[OUTPUT+i]=(i*19+self.case.seed*7+0x31)&255
        elif t==RANDOM:answer=draw(self.case,n)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000000;self.r[2]=answer

def check(words,c):
    initial=fixture(c);expected,calls,observations=reference(initial,c);m=Oracle(words,initial,c);m.run()
    assert public(m.memory)==expected,('memory',c,[(hex(p),expected[p],public(m.memory).get(p)) for p in expected if public(m.memory).get(p)!=expected[p]][:8])
    assert m.calls==calls,('calls',c,m.calls,calls)
    assert m.observed==observations,('packet',c,m.observed,observations)
    return m

def main():
    programs=s.programs();coverage=Counter();visited=set();n=0
    for c in cases():
        for i,words in enumerate(programs):
            m=check(words,c)
            if not i:coverage.update(t for t,a in m.calls);visited.update(m.visits)
        n+=1
    assert set(coverage)=={FACTORY,ALLOC,DECODE,READ,DEBRIS,SPRAY,CONFIG,RANDOM,EMIT}
    report=dict(cases=n,streams=2,original_constructor_words=48,original_decoder_words=5,constructor_payload_bytes=44,
        read_policies=3,config_words=49,descriptor_defined_bytes=5,descriptor_padding_bytes_uncredited=1,
        visited_retail_words=sum(s.ENTRY<=v<s.ENTRY+s.SIZE for v in visited),coverage={hex(t):v for t,v in coverage.items()},
        finite_only=True,installed=False,c_match_credit=0)
    (s.OUT/'oracle-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
