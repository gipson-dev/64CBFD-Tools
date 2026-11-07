"""Independent float32 field model; original updater connection, not FCSR emulation."""
from dataclasses import dataclass,replace
import itertools,math,struct
from unittest.mock import patch
from tools.experiments import game_record_motion_update_1513e6e8_candidates as c
from tools.tests import game_dual_record_animation_update_1513cfe4_oracle as updater
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as ram
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating

ENTRY,TIME,RESOURCE,FOLLOW,STACK=0x1513E6E8,0x800BE9A4,updater.RESOURCE,updater.FOLLOW,updater.STACK
u32,rd,wr,state=ram.u32,ram.rd,ram.wr,ram.state
GROUPS=((0x20,((0x11C,0x13C),)),(0x40,((0x34,0x118),(0x38,0x11C),(0x3C,0x120))),(0x80,((0x40,0x124),(0x44,0x128),(0x48,0x12C))),(0x100,((0x4C,0x130),(0x50,0x134),(0x54,0x138))))
DESTINATIONS=tuple(range(0x34,0x58,4));SOURCES=tuple(range(0x118,0x140,4))
PATTERNS=((0,0x80000000,0x3F800000,0xBFC00000,0x4B800000,0x3EAAAAAB),
          (1,0x80000001,0x00800000,0x80800000,0x007FFFFF,0x807FFFFF),
          (0x3F000001,0xBF000001,0x4B800001,0xCB800001,0x3E800000,0xBE800000),
          (0x7F7FFFFF,0xFF7FFFFF,0x3F800000,0xBF800000,0,0x80000000),
          (0x7FC12345,0x7F800000,0xFF800000,0,0x80000000,0x3F800000))

@dataclass(frozen=True)
class Case:
    flags:int=0x1E0
    time:int=0x3F800000
    pattern:int=0
    alias:int=0
    phase:int=0
    seed:int=0

def symbols():return dict(D_800BE9A4=TIME)
def base(case):return RESOURCE if not case.alias else TIME-0x11C if case.alias==1 else TIME-0x34

def fields(m,p,case,order='big'):
    values=PATTERNS[case.pattern]
    for i,off in enumerate((*DESTINATIONS,*SOURCES)):wr(m,p+off,values[(i+case.seed)%len(values)],4,order)
    wr(m,p+0x58,case.flags,4,order)

def fixture(case=Case(),order='big'):
    p=base(case);regions=[(p,512),(STACK+case.phase-1024,1536)]
    if not p<=TIME<TIME+4<=p+512:regions.append((TIME,4))
    seen=set();m={}
    for a,n in regions:
        addresses={u32(a+i)for i in range(n)};assert not seen&addresses,'Disjoint banks except explicit contained time alias';seen|=addresses
        m.update({u32(a+i):(i*29+case.seed*11+90)&255 for i in range(n)})
    fields(m,p,case,order);wr(m,TIME,case.time,4,order);return m

def public(m,case):return {p:v for p,v in m.items()if not STACK+case.phase-1024<=p<STACK+case.phase+512}

def reference(initial,case=Case(),order='big',record=None):
    m=dict(initial);p=base(case)if record is None else record
    for flag,pairs in GROUPS:
        if rd(m,p+0x58,4,order)&flag:
            for dest,source in pairs:
                product=bits(floating(rd(m,p+source,4,order))*floating(rd(m,TIME,4,order)))
                result=bits(floating(rd(m,p+dest,4,order))+floating(product))
                wr(m,p+dest,result,4,order)
    m[p+0x5D]=255
    return dict(memory=m,observed=public(m,case),calls=[],value=1)

class FloatInstructions:
    def execute(self,w):
        if w>>26!=17:return super().execute(w)
        fmt,ft,fs,fd,fn=w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        assert fmt==16 and fn in(0,2),hex(w)
        a,b=floating(self.f[fs]),floating(self.f[ft]);self.f[fd]=bits(a+b if fn==0 else a*b);self.r[0]=0

class Oracle(FloatInstructions,FactoryOracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,arguments=None):
        super().__init__(words,memory,case,entry=entry,s=symbols(),connected=connected,arguments=arguments or(base(case),))
    def record_call(self,t):raise AssertionError('Leaf emitted a call: '+hex(t))
    def hook(self,t):raise AssertionError('Leaf used a provider: '+hex(t))

class UpdaterOracle(FloatInstructions,updater.Oracle):pass

def connected_case(motion=Case(),enabled=1,second=1,result=1,veto=1,mutation=0):
    return updater.Case(flags=motion.flags,enabled=enabled,update=1,second=second,exit=1,answer=1,second_answer=result,exit_answer=veto,mutation=mutation,phase=motion.phase,seed=motion.seed,cursor=65536)

def connected_fixture(motion,case,order='big'):
    assert not motion.alias
    m=updater.fixture(case,order)
    for p in(RESOURCE,FOLLOW):
        for i in range(256,512):assert p+i not in m;m[p+i]=(i*29+case.seed*11+90)&255
        fields(m,p,motion,order)
    assert all(TIME+i not in m for i in range(4));wr(m,TIME,motion.time,4,order)
    return m

def connected_reference(initial,motion,case):
    original=updater.effect
    def service(m,uc,stage,home,record,order='big'):
        if stage==0 and m[record+0x70]==1:
            e=reference(m,motion,order,record);m.clear();m.update(e['memory'])
        else:original(m,uc,stage,home,record,order)
    with patch.object(updater,'effect',service):return updater.reference(initial,case)

def cases():
    for flags,time,pattern,phase in itertools.product(range(0,512,32),(0,0x80000000,0x3F800000,0xBF800000,0x3EAAAAAB,0x40000000,0x7FC12345),range(5),(0,8)):
        yield Case(flags=flags,time=time,pattern=pattern,phase=phase,seed=pattern)
    for flags in range(512):yield Case(flags=flags,seed=flags%3)
    for alias,flags,time in itertools.product((1,2),range(0,512,32),(0x3F800000,0x3F000000,0xBF800000)):
        yield Case(alias=alias,flags=flags,time=time)
    yield Case(flags=0xFFFFFFFF)
    yield Case(flags=0x800001E0)

def native_cases():
    result=[]
    for case in cases():
        if case.alias or case.phase or case.pattern==4 or not math.isfinite(floating(case.time)):continue
        initial=fixture(case);e=reference(initial,case)
        if all(math.isfinite(floating(rd(e['memory'],RESOURCE+off)))for off in(*DESTINATIONS,*SOURCES)):result.append(case)
    return tuple(result)
