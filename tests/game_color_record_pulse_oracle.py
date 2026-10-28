"""Ordered big-endian color-record model with explicit helper and incoming-home effects."""
from dataclasses import dataclass
from tools.experiments import game_color_record_pulse_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,OTHER,NEXT=0x22000,0x23000,0x24000
COUNT,SLOTS=0x800DD190,0x800DD198
@dataclass(frozen=True)
class Case:
    lifetime:int=100
    ticks:int=2
    red:int=180
    state:int=0
    callback:int=1
    mutation:int=0
    redirect:bool=False
    clock_alias:int=-1
    phase:int=0

def fixture(c,ticks=None):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-768,512)}
    for base in(RECORD,OTHER):
        m.update({base+i:(i*13+0x59)&255 for i in range(-16,96)})
        for off,v,size in((0,0x5A,1),(8,NEXT,4),(0x10,c.lifetime if base==RECORD else 7,4),(0x15,c.red if base==RECORD else 254,1),(0x18,c.state if base==RECORD else 3,1),(0x19,c.callback,1)):put(m,base+off,v&((1<<(size*8))-1),size)
    clock=RECORD+c.clock_alias if c.clock_alias>=0 else source.TICKS if ticks is None else ticks
    if c.clock_alias<0:put(m,clock,c.ticks&0xFFFFFFFF)
    put(m,source.MODE_GLOBAL,0xFEEDFACE)
    return m,clock

def mode_effect(m,c,clock):
    put(m,source.MODE_GLOBAL,2)
    if c.mutation&1:m[RECORD+0x15]=255;m[RECORD+0x18]=3
    if c.mutation&2:put(m,clock,0xFFFFFFFF)
    if c.mutation&4:put(m,RECORD+8,NEXT+0x100)
    if c.redirect:put(m,STACK+c.phase,OTHER)

def free_effect(m,record):m[record+0x1F]^=0xA5

def reference(initial,c,clock):
    m=dict(initial);record=RECORD;calls=[];remaining=read(m,record+0x10)
    if remaining:
        remaining=signed((remaining-read(m,clock))&0xFFFFFFFF)
        if remaining<=0:
            calls.append((source.FREE,(record,)));free_effect(m,record);return m,calls
        put(m,record+0x10,remaining)
    if m[record+0x19]==0:
        calls.append((source.MODE,(2,)));mode_effect(m,c,clock)
        if c.redirect:record=read(m,STACK+c.phase)
    step=(read(m,clock)*2)&0xFFFFFFFF;shade=m[record+0x15]
    if m[record+0x18]==0:
        shade=signed((shade-step)&0xFFFFFFFF)
        if shade<144:shade=144;m[record+0x18]=1
    else:
        shade=signed((shade+step)&0xFFFFFFFF)
        if shade>=256:shade=255;m[record+0x18]=0
    m[record+0x15]=shade&255
    return m,calls

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+512}

class PulseOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,free=source.FREE,mode=source.MODE):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected);self.case,self.trace,self.free,self.mode=c,[],free,mode;self.clock=RECORD+c.clock_alias if c.clock_alias>=0 else source.TICKS
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target in(self.mode,self.free,source.ENTRY,source.SCAN,source.ADAPTER,source.UNLINK),hex(target)
        args=self.arguments(2 if target==source.UNLINK else 1);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target==self.mode:
            assert self.r[4]==2;mode_effect(self.memory,self.case,self.clock)
        else:
            assert target in(self.free,source.UNLINK)
            if target==source.UNLINK:assert self.r[5]==1
            free_effect(self.memory,self.r[4])
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.owner.window_end:raise WindowBoundary
        return super().__getitem__(pc)
