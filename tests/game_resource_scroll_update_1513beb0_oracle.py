"""Independent float32 scroll model and bounded guest execution, without FCSR."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,math,struct
from tools.experiments import game_resource_scroll_update_1513beb0_candidates as c
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle

ENTRY,WRAP,SINE,CALLER=0x1513BEB0,0x15144B68,0x15047D60,0x1513B798
RESOURCE,COEFF,TIME,BOUND=0x50000,0x800A4A84,0x800BE9A4,0x800A56A4
TABLE,TICKS,RELEASE=0x80089C18,0x800BE9E4,0x1516972C
STACK,u32,bits,floating,rd,wr=fp.STACK,fp.u32,fp.bits,fp.floating,fp.rd,fp.wr
add,sub,mul=fp.add,fp.sub,fp.mul
REGIONS=((RESOURCE,2048),(COEFF-16,64),(TIME-16,64),(BOUND-4,16))

@dataclass(frozen=True)
class Case:
    scroll:int=0
    phaseValue:int=0
    angleS:int=0
    angleT:int=0
    time:int=0x3F800000
    sine:int=0x3E800000
    mutation:int=0
    alias:int=0
    connected:int=0
    seed:int=0
    phase:int=0
    base:int=RESOURCE

def symbols():
    s={n:int(n[2:],16)for n in('D_800A4A84','D_800A4A88','D_800A4A8C','D_800A4A90','D_800A4A94','D_800BE9A4')}
    return dict(s,func_15144B68=WRAP,sinf=SINE)

@lru_cache(None)
def retained():
    rom=(c.ROOT/'conker/conker.us.bin').read_bytes()
    return tuple(struct.unpack_from('>5I',rom,0x249544)),struct.unpack_from('>I',rom,0x24A164)[0]

def payload(m,case,order='big'):return u32(case.base+rd(m,case.base+0x50,4,order)+0xF8)

def fixture(case=Case(),order='big'):
    regions=(*REGIONS,(STACK+case.phase-1024,1536))
    m={u32(a+i):(i*29+case.seed*11+90)&255 for a,n in regions for i in range(n)}
    if case.base!=RESOURCE:
        m.update({u32(case.base+i):(i*29+case.seed*11+90)&255 for i in range(512)})
    coeff,bound=retained()
    for i,w in enumerate(coeff):wr(m,COEFF+4*i,w,4,order)
    wr(m,BOUND,bound,4,order);wr(m,TIME,case.time,4,order)
    at=RESOURCE+0x2F8 if not case.alias else TIME if case.alias==1 else COEFF
    wr(m,case.base+0x50,u32(at-case.base-0xF8),4,order)
    for i,w in enumerate((case.scroll,bits(91.0),case.phaseValue,case.angleS,case.angleT)):wr(m,at+4*i,w,4,order)
    return m

def public(m,case):return {p:v for p,v in m.items()if not STACK+case.phase-1024<=p<STACK+case.phase+512}

def wrap(value,bound):
    # Finite bounded fixtures only. The retail loops need not terminate for infinity.
    count=0
    while bound<value:
        value=sub(value,bound);count+=1;assert count<1000
    while value<0.0:
        value=add(value,bound);count+=1;assert count<1000
    return value

def effect(m,case,order='big'):
    at=RESOURCE+0x2F8 if not case.alias else TIME if case.alias==1 else COEFF
    if case.mutation==1:
        wr(m,TIME,bits(2.5),4,order);wr(m,COEFF+12,bits(0.5),4,order);wr(m,COEFF+16,bits(-0.25),4,order)
    if case.mutation==2:
        wr(m,at+12,bits(-18.0),4,order);wr(m,at+16,bits(19.0),4,order);wr(m,case.base+0x50,0x400,4,order)
    if case.mutation==3:wr(m,at,bits(-8193.5),4,order)

def reference(initial,case=Case(),order='big'):
    m=dict(initial);calls=[];at=payload(m,case,order)
    get=lambda p:floating(rd(m,p,4,order))
    put=lambda p,v:wr(m,p,bits(v),4,order)
    def bounded_wrap(value):
        calls.append((WRAP,(bits(value),)))
        return wrap(value,get(BOUND))
    put(at+8,add(get(at+8),mul(get(COEFF),get(TIME))))
    phase=bounded_wrap(get(at+8));put(at+8,phase)
    put(at,add(get(at),mul(get(COEFF+4),get(TIME))))
    calls.append((SINE,(bits(phase),)));effect(m,case,order)
    put(at+4,mul(floating(case.sine),get(COEFF+8)))
    put(at+12,add(get(at+12),mul(get(COEFF+12),get(TIME))))
    put(at+16,add(get(at+16),mul(get(COEFF+16),get(TIME))))
    put(at+12,bounded_wrap(get(at+12)));put(at+16,bounded_wrap(get(at+16)))
    for off in(0,4):
        while get(at+off)>4096.0:put(at+off,sub(get(at+off),4096.0))
        while get(at+off)<0.0:put(at+off,add(get(at+off),4096.0))
    return dict(memory=m,observed=public(m,case),calls=calls,value=1)

def helpers(rom,case):
    return dict(zip(range(WRAP,WRAP+96,4),struct.unpack_from('>24I',rom,0x172018)))if case.connected else{}

class Oracle(fp.Oracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,arguments=None):
        self.home=STACK+case.phase
        FactoryOracle.__init__(self,words,memory,case,entry=entry,s=symbols(),connected=connected,arguments=arguments or(case.base,))
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==60:
            self.condition=floating(self.f[w>>11&31])<floating(self.f[w>>16&31]);self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        assert t in(ENTRY,WRAP,SINE,RELEASE),hex(t)
        a=(self.f[12],)if t in(WRAP,SINE)else tuple(map(u32,self.arguments(1)))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t in(WRAP,SINE,RELEASE)
        result=bits(wrap(floating(self.f[12]),floating(rd(self.memory,BOUND))))if t==WRAP else self.case.sine
        if t==SINE:effect(self.memory,self.case)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=result;self.r[2]=0xA5000002

state=fp.state

def cases():
    for scroll,sine,time in itertools.product((0.0,-0.0,4096.0,4096.25,-0.25,8192.5,-8192.5),(0.0,0.25,-1.0,100.0,-100.0),(0.0,1.0)):
        yield Case(scroll=bits(scroll),sine=bits(sine),time=bits(time))
    for v in(0.0,-0.0,6.2831854820251465,6.283186,-0.000001,20.0,-20.0):
        yield Case(phaseValue=bits(v),angleS=bits(v),angleT=bits(-v))
    for mutation,phase in itertools.product((1,2,3),(0,8)):
        yield Case(mutation=mutation,phase=phase)
    for alias in(1,2):yield Case(alias=alias,scroll=bits(0.125),angleS=bits(0.75),angleT=bits(-0.5))
    for value in(200.0,-200.0):yield Case(sine=bits(value))
