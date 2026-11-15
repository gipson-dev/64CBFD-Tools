"""State callback semantics with the original 48-word type-7 constructor."""
from dataclasses import dataclass
from collections import Counter
from functools import lru_cache
import hashlib,json,math,struct
from tools.experiments import game_impact_phase_150c3994_match as s
from tools.experiments import game_type07_parameter_record_match as factory
from tools.tests.game_actor_motion_150c3574_qualification import Oracle as BaseOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

OWNER,OUTPUT,MARK,COEFF=0x30040,0x50040,0x70000,0x800A0334
FACTORY,ALLOC,BUFFER,AUDIO,BURST,MASK,SOUND,MOVE,EXIT,STATE=(
    0x151B9BF0,0x15167A68,0x15188810,0x10010630,0x150C1660,
    0x1506AC8C,0x10010344,0x15059140,0x150C3D5C,0x15060F28)
FLOATS=(0x14,0x18,0x1C,0x20,0x28,0x40,0xB8,0x114,0x148)
WORDS=(0,0xF8,0x2E4);HALVES=(0x7A,0xCC)
signed16=lambda n:((n&65535)^32768)-32768
u32=lambda n:n&0xFFFFFFFF
add=lambda a,b:fp(a,b,'add')
mul=lambda a,b:fp(a,b,'mul')

@dataclass(frozen=True)
class Case:
    seed:int=0
    phase:int=0
    state:int=20
    counter:int=0
    marker:int=0
    velocity:int=0xBF800000
    timer:int=0x42200000
    flag136:int=0
    flag107:int=0
    flag1ca:int=1
    halfCC:int=0
    mutation:int=0
    outcome:int=1

def cases():
    for i in range(2048):
        yield Case(i,i%2*8,19+i%2,(0,1,9,10,19,20,21,254,255)[i%9],i//2%2,
            bits((0.,1.,-1.,-2.,-100.)[i//4%5]),bits((0.,20.,20.000001907348633,21.,40.,10000.)[i//20%6]),
            i//120%2,i//240%2,i//480%2,(0,-1,32767,-32768)[i//960%4],i//9%3,i//27%3)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
    for base,n in ((OWNER-32,0x340),(OUTPUT-32,192),(MARK,4),(COEFF,4)):
        m.update({base+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
    put(m,OWNER,c.state);put(m,OWNER+0x2E4,c.marker);put(m,OWNER+0xF8,0xA5128040^c.seed)
    for off,v in ((0x83,c.counter),(0x136,c.flag136),(0x107,c.flag107),(0x1CA,c.flag1ca)):
        m[OWNER+off]=v
    coords=(-65536.5,-32768.75,0.,32767.75,65536.5)
    for off,v in ((0x14,bits(coords[c.seed%5])),(0x18,bits(coords[c.seed//5%5]-30.)),(0x1C,bits(coords[c.seed//25%5])),
        (0x20,c.velocity),(0x28,c.timer),(0x40,bits(1.)),(0xB8,bits((0.,10.,-10.)[c.seed%3])),(0x114,bits(3.)),(0x148,bits((0.,-2.,4.)[c.seed%3]))):put(m,OWNER+off,v)
    put(m,OWNER+0x7A,(0,0x3FFF,0x4000,0x7FFF,0x8000,0xFFFF)[c.seed%6],2);put(m,OWNER+0xCC,c.halfCC,2)
    put(m,MARK,0);put(m,COEFF,0x3F75C28F)
    return m

def public(m):return {p:v for p,v in m.items() if not STACK-1024<=p<STACK+1024}

def effect(m,c,t,n):
    put(m,MARK,u32(0x13579BDF+t+n*0x10203))
    if not c.mutation:return
    if t==ALLOC:
        if c.mutation==1:put(m,OWNER+0x2E4,1)
        else:m[OWNER+0x83]=0
    elif t==BUFFER:
        put(m,OWNER+0x2E4,0)
        if c.mutation==2:m[OWNER+0x83]=0
    elif t==AUDIO:
        if c.mutation==2:m[OWNER+0x83]=0
    elif t==BURST:
        put(m,OWNER+0x14,bits(17.));put(m,OWNER+0x18,bits(-25.));put(m,OWNER+0x1C,bits(35.))
    elif t==MASK:m[OWNER+0x83]=255;put(m,OWNER+0xF8,0x80000000)
    elif t==SOUND:m[OWNER+0x83]=(9,20,255)[c.seed%3];put(m,OWNER+0xF8,0x12340000)
    elif t==MOVE:
        put(m,OWNER+0x148,bits(-5.));put(m,OWNER+0xB8,bits(13.))
        if c.mutation==2:put(m,OWNER+0x28,0);m[OWNER+0x107]=1
    elif t==EXIT:m[OWNER+0xD0]^=0x55
    elif t==STATE:m[OWNER+0xD0]^=0xA3

def allocation(c,n):return OUTPUT+64*n if c.outcome==1 or c.outcome==2 and n%2==0 else 0
def initialize(m,c,n,p):
    for i in range(44):m[p+i]=(i*19+c.seed*7+n*23+0x31)&255

def reference(initial,c):
    m=dict(initial);calls=[];counts=Counter();allocated=[]
    def call(t,*args):
        calls.append((t,tuple(map(u32,args))));n=counts[t];counts[t]+=1
        effect(m,c,t,n)
        if t==ALLOC:
            p=allocation(c,n)
            if p:initialize(m,c,n,p);allocated.append(p)
            return p
        return 0xD00D0000
    def emit(values):
        args=(47,1,*(signed16(math.trunc(floating(read(m,OWNER+off) if off!=0x18 else add(read(m,OWNER+off),bits(30.)))) ) for off in (0x14,0x18,0x1C)),*values,0,255,0)
        assert len(args)==16
        calls.append((FACTORY,tuple(map(u32,args))))
        p=call(ALLOC,7,args[15],44,0,args[14],1)
        if p:
            m[p+20]=args[0]&255;m[p+21]=args[1]&255;put(m,p+16,args[13])
            for i,v in enumerate(args[2:13]):put(m,p+22+2*i,v,2)
    if read(m,OWNER)==20:
        if not read(m,OWNER+0x2E4):emit((2000,1000,400,200,3072,3072,1,1))
        else:call(BUFFER,OWNER,100,0)
    v,timer=read(m,OWNER+0x20),read(m,OWNER+0x28)
    if floating(v)<0. and 20.<floating(timer) and not m[OWNER+0x136] and floating(timer)<floating(mul(bits(-20.),v)):
        call(AUDIO,0x92,OWNER,32000,200,2500);m[OWNER+0x136]=1
    if not m[OWNER+0x83]:
        put(m,OWNER+0x148,bits(70.))
        if not read(m,OWNER+0x2E4):
            emit((2200,1280,800,700,3072,3072,20,1))
            call(BURST,read(m,OWNER+0x14),add(read(m,OWNER+0x18),bits(30.)),read(m,OWNER+0x1C),255)
            call(MASK,OWNER,6,0)
        else:call(BUFFER,OWNER,100,0)
        call(SOUND,0x1A9,OWNER,32767,1000,2000)
        put(m,OWNER+0x114,bits(500.));m[OWNER+0xD0]=1;put(m,OWNER+0xF8,read(m,OWNER+0xF8)|0x01008000)
    m[OWNER+0x125]=255;m[OWNER+0x83]=(m[OWNER+0x83]+1)&255
    if m[OWNER+0x83]>=11:put(m,OWNER+0xF8,read(m,OWNER+0xF8)&0xFFFF7FFF)
    put(m,OWNER+0x40,mul(bits(float(read(m,OWNER+0x7A,2)+16384)),bits(.0054931640625)))
    call(MOVE,OWNER)
    put(m,OWNER+0xB8,add(read(m,OWNER+0xB8),read(m,OWNER+0x148)))
    put(m,OWNER+0x148,mul(read(m,OWNER+0x148),read(m,COEFF)))
    if (floating(read(m,OWNER+0x28))==0. and m[OWNER+0x83]>=21 and signed16(read(m,OWNER+0xCC,2))==0) or m[OWNER+0x107] or not m[OWNER+0x1CA]:
        call(EXIT,OWNER);call(AUDIO,0x93,OWNER,32000,200,2500);call(STATE,OWNER,1)
    return public(m),calls,allocated

@lru_cache(maxsize=1)
def helper_code():
    rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes();data=rom[factory.ROM:factory.ROM+factory.SIZE]
    assert hashlib.sha256(data).hexdigest()==factory.TRUTH_SHA
    return dict(zip(range(FACTORY,FACTORY+len(data),4),struct.unpack('>48I',data)))

class Oracle(BaseOracle):
    def __init__(self,words,initial,c,entry=s.ENTRY,connected=None):
        code=dict(helper_code());code.update(connected or {})
        super().__init__(words,initial,c,entry=entry,connected=code)
        self.counts=Counter();self.entries=[];self.allocated=[]
    def record_call(self,t):
        if t==s.ENTRY:self.entries.append(self.r[4]);return
        if t==FACTORY:
            a=list(self.arguments(16));a[2:13]=[u32(signed16(v)) for v in a[2:13]];a[14]&=255;a=tuple(a)
        elif t==ALLOC:a=tuple(self.arguments(6))
        elif t in (BUFFER,MASK):a=tuple(self.arguments(3))
        elif t in (AUDIO,SOUND):a=tuple(self.arguments(5))
        elif t==BURST:a=(self.f[12],self.f[14],self.r[6],self.r[7])
        elif t in (MOVE,EXIT):a=(self.r[4],)
        elif t==STATE:a=tuple(self.arguments(2))
        else:raise AssertionError(hex(t))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t!=FACTORY,'The actual constructor must execute'
        n=self.counts[t];self.counts[t]+=1;effect(self.memory,self.case,t,n);answer=0xD00D0000
        if t==ALLOC:
            answer=allocation(self.case,n)
            if answer:initialize(self.memory,self.case,n,answer);self.allocated.append(answer)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000000;self.r[2]=answer

def check(words,c):
    initial=fixture(c);expected,calls,allocated=reference(initial,c);m=Oracle(words,initial,c);m.run()
    assert public(m.memory)==expected,('memory',c,[(hex(p),expected[p],public(m.memory).get(p)) for p in expected if public(m.memory).get(p)!=expected[p]][:10])
    assert m.calls==calls,('calls',c,m.calls,calls)
    assert m.allocated==allocated
    return m

def main():
    programs=s.programs();coverage=Counter();visited=set();n=0
    for c in cases():
        for i,words in enumerate(programs):
            m=check(words,c)
            if not i:coverage.update(t for t,a in m.calls);visited.update(m.visits)
        n+=1
    assert set(coverage)=={FACTORY,ALLOC,BUFFER,AUDIO,BURST,MASK,SOUND,MOVE,EXIT,STATE}
    report=dict(cases=n,streams=3,original_constructor_words=48,finite_only=True,
        constructor_payload_bytes=44,allocator_policies=3,helpers='bounded modeled providers; original constructor connected',
        coverage={hex(t):v for t,v in coverage.items()},visited_target_words=sum(s.ENTRY<=v<s.ENTRY+s.SIZE for v in visited))
    (s.OUT/'oracle-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
