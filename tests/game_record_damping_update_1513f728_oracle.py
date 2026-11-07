"""Independent float32 damping/midpoint model, bounded RAM and original updater."""
from dataclasses import dataclass,replace
import itertools,math
from unittest.mock import patch
from tools.tests import game_dual_record_animation_update_1513cfe4_oracle as updater
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as ram
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating

ENTRY,TIME,INVERSE,TICKS=0x1513F728,0x800BE9A4,0x800BE9A8,0x800BE9E4
RESOURCE,FOLLOW,STACK=updater.RESOURCE,updater.FOLLOW,updater.STACK
u32,rd,wr,state=ram.u32,ram.rd,ram.wr,ram.state
OFFSETS=(*range(0x34,0x4C,4),*range(0x110,0x130,4))
PATTERNS=((0x3F800000,0xC0000000,0x3EAAAAAB,0xBF000000,0x40000000,0x3F000001),
          (0,0x80000000,0x3F800000,0xBF800000,0,0x80000000),
          (1,0x80000001,0x00800000,0x80800000,0x007FFFFF,0x807FFFFF),
          (0x4B800001,0xCB800001,0x3F000001,0xBF000001,0x3EAAAAAB,0x3DCCCCCD),
          (0x7FC12345,0x7F800000,0xFF800000,0,0x80000000,0x7F7FFFFF))

@dataclass(frozen=True)
class Case:
    ticks:int=1
    time:int=0x3F000000
    inverse:int=0x40000000
    damping:int=0x3F400000
    pattern:int=0
    alias:int=0
    phase:int=0
    seed:int=0

def symbols():return dict(D_800BE9A4=TIME,D_800BE9A8=INVERSE,D_800BE9E4=TICKS)
def base(c):return (RESOURCE,TIME-0x34,TIME-0x110,TIME-0x120,TICKS-0x110)[c.alias]

def fields(m,p,c,order='big'):
    for i,off in enumerate(OFFSETS):wr(m,p+off,PATTERNS[c.pattern][(i+c.seed)%6],4,order)
    wr(m,p+0x120,c.damping,4,order)

def fixture(c=Case(),order='big'):
    p=base(c);regions=[(p,512),(STACK+c.phase-1024,1536)]
    if not p<=TIME<TIME+80<=p+512:regions.append((TIME,80))
    m={};seen=set()
    for a,n in regions:
        addresses={u32(a+i)for i in range(n)};assert not addresses&seen,'Fixture regions must be disjoint';seen|=addresses
        for i in range(n):m[u32(a+i)]=(i*29+c.seed*11+90)&255
    fields(m,p,c,order)
    for a,v in((TIME,c.time),(INVERSE,c.inverse),(TICKS,c.ticks)):wr(m,a,v,4,order)
    return m

def public(m,c):return {p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}

def reference(initial,c=Case(),order='big',record=None):
    m=dict(initial);p=base(c)if record is None else record
    previous=[floating(rd(m,p+off,4,order))for off in(0x110,0x114,0x118)]
    ticks=rd(m,TICKS,4,order);assert ticks<=64,'Finite reference corpus bound, never a source clamp'
    for _ in range(ticks):
        damping=floating(rd(m,p+0x120,4,order))
        for off in(0x110,0x114,0x118):wr(m,p+off,bits(ram.mul(floating(rd(m,p+off,4,order)),damping)),4,order)
    gravity=ram.mul(floating(rd(m,p+0x11C,4,order)),floating(rd(m,TIME,4,order)))
    wr(m,p+0x114,bits(ram.add(floating(rd(m,p+0x114,4,order)),gravity)),4,order)
    inverse=floating(rd(m,INVERSE,4,order))
    acceleration=[ram.mul(ram.sub(floating(rd(m,p+off,4,order)),old),inverse)for off,old in zip((0x110,0x114,0x118),previous)]
    for off,old,rate in zip((0x34,0x38,0x3C),previous,acceleration):
        time=floating(rd(m,TIME,4,order));midpoint=ram.add(old,ram.mul(ram.mul(0.5,rate),time))
        wr(m,p+off,bits(ram.add(floating(rd(m,p+off,4,order)),ram.mul(midpoint,time))),4,order)
    for off,source in zip((0x40,0x44,0x48),(0x124,0x128,0x12C)):
        product=ram.mul(floating(rd(m,p+source,4,order)),floating(rd(m,TIME,4,order)))
        wr(m,p+off,bits(ram.add(floating(rd(m,p+off,4,order)),product)),4,order)
    return dict(memory=m,observed=public(m,c),calls=[],value=1)

class FloatInstructions:
    def execute(self,w):
        if w>>26!=17:return super().execute(w)
        fmt,ft,fs,fd,fn=w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if fmt==4:self.f[fs]=self.r[ft]
        else:
            assert fmt==16 and fn in(0,1,2),hex(w)
            a,b=floating(self.f[fs]),floating(self.f[ft]);self.f[fd]=bits((ram.add,ram.sub,ram.mul)[fn](a,b))
        self.r[0]=0

class Oracle(FloatInstructions,FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols(),connected=connected,arguments=arguments or(base(c),))
    def record_call(self,t):raise AssertionError('Leaf emitted a call: '+hex(t))
    def hook(self,t):raise AssertionError('Leaf used a provider: '+hex(t))

class UpdaterOracle(FloatInstructions,updater.Oracle):pass

def connected_case(c=Case(),enabled=1,second=1,result=1,veto=1,mutation=0):
    assert not c.alias
    return updater.Case(enabled=enabled,update=25,second=second,exit=1,answer=1,second_answer=result,exit_answer=veto,mutation=mutation,phase=c.phase,seed=c.seed,cursor=65536,ticks=c.ticks,timer=20)

def connected_fixture(c,uc,order='big'):
    m=updater.fixture(uc,order)
    for p in(RESOURCE,FOLLOW):
        for i in range(256,512):assert p+i not in m;m[p+i]=(i*29+c.seed*11+90)&255
        fields(m,p,c,order)
    # The updater's tick bank starts at E9C4. Fill only its missing prefix;
    # all symbols share one explicitly nonoverlapping ordinary-RAM arena.
    for i in range(80):
        if TIME+i not in m:m[TIME+i]=(i*29+c.seed*11+90)&255
    wr(m,TIME,c.time,4,order);wr(m,INVERSE,c.inverse,4,order)
    return m

def connected_reference(initial,c,uc):
    original=updater.effect
    def service(m,case,stage,home,record,order='big'):
        if stage==0 and m[record+0x70]==25:
            e=reference(m,c,order,record);m.clear();m.update(e['memory'])
        else:original(m,case,stage,home,record,order)
    with patch.object(updater,'effect',service):return updater.reference(initial,uc)

def cases():
    for ticks,pattern,damping,phase in itertools.product((0,1,2,3,4,5,7,8,9,15,16,17,31),range(5),(0x3F400000,0x3F800000,0xBF000000),(0,8)):
        yield Case(ticks=ticks,pattern=pattern,damping=damping,phase=phase,seed=pattern)
    for alias,ticks,time in itertools.product((1,2,3,4),(0,1,2,3,4,5,8),(0,0x80000000,0x3F000000,0xBF800000)):
        yield Case(alias=alias,ticks=ticks,time=time)
    for time,inverse in itertools.product((0,0x80000000,1,0x3F000001,0xBF000001,0x7F800000,0x7FC12345),(0,0x3F800001,0xBF000001)):
        yield Case(time=time,inverse=inverse,ticks=3)

def native_cases():
    result=[]
    for c in cases():
        if c.alias or c.phase or c.pattern==4 or not all(math.isfinite(floating(v))for v in(c.time,c.inverse,c.damping)):continue
        e=reference(fixture(c),c)
        if all(math.isfinite(floating(rd(e['memory'],RESOURCE+off)))for off in OFFSETS):result.append(c)
    return tuple(result)
