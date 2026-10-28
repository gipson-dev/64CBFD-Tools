"""Ordered O32 homes, narrowing stores, allocator effects and constructor callers."""
from dataclasses import dataclass
from tools.experiments import game_type07_parameter_record_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
OUTPUT,PREVIOUS,ACTOR=0x200000,0x201000,0x202000
DEFAULT=tuple((0xA5000000+i*0x13579)&0xFFFFFFFF for i in range(16))
@dataclass(frozen=True)
class Case:
    args:tuple=DEFAULT
    fail:bool=False
    mutation:int=0
    home:object=None
    phase:int=0

def destination(c,sp):return 0 if c.fail else OUTPUT if c.home is None else(sp+c.home)&0xFFFFFFFF
def packet(args):return(7,args[15]&0xFFFFFFFF,44,0,args[14]&255,1)
def head(args):return source.LIST+(args[15]&255)*0x1A0+28

def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,0x900)}
    for base in(OUTPUT,PREVIOUS,ACTOR):m.update({base+i:(i*13+0x59)&255 for i in range(-16,0x400)})
    for i,v in enumerate(c.args):put(m,STACK+c.phase+4*i,v&0xFFFFFFFF)
    put(m,head(c.args),0)
    return m

def effect(m,c,sp,call_sp):
    if c.mutation&1:
        for i in range(16):put(m,sp+4*i,(0x76543210+i*0x01010101)&0xFFFFFFFF)
    result=destination(c,sp)
    if c.mutation&2 and result:m[result+2]^=0xA5
    for i in range(4):put(m,call_sp+4*i,0xB5000000+i)

def stores(m,sp,out):
    put(m,out+20,read(m,sp)&255,1);put(m,out+21,read(m,sp+4)&255,1)
    for i in range(11):put(m,out+22+i*2,read(m,sp+4*(i+2)+2,2),2)
    put(m,out+16,read(m,sp+52))

def reference(initial,c,sp=None,initialize=False):
    sp=STACK+c.phase if sp is None else sp;m=dict(initial)
    for i,v in enumerate(c.args):put(m,sp+4*i,v&0xFFFFFFFF)
    args=packet(c.args);out=destination(c,sp)
    if initialize:
        assert c.mutation==0 and c.home is None
        if out:
            m[out+1]=args[1]&255;h=head(c.args);old=read(m,h);put(m,out+8,old)
            if old:put(m,old+4,out)
            m[out]=7;put(m,out+4,0);put(m,h,out);m[out+12]=args[4]
    else:effect(m,c,sp,sp-32)
    if out:stores(m,sp,out)
    return m,args,out

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+0x900}

class ConstructorOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,factory=source.FACTORY,arguments=None,child_sp=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=c.args if arguments is None else arguments,connected=connected)
        self.case,self.trace,self.factory=c,[],factory;self.child_sp=STACK+c.phase if child_sp is None else child_sp;self.target_entries=[];self.drop_late=False
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        if target==source.ENTRY:
            self.child_sp=self.r[29];args=self.arguments(16);self.target_entries.append(args)
        else:
            sizes={self.factory:6,source.HEAP:5,source.INITIALIZER:2};assert target in sizes,hex(target);args=self.arguments(sizes[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in(self.factory,source.HEAP)
        if target==self.factory:effect(self.memory,self.case,self.child_sp,self.r[29])
        else:
            for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        if self.drop_late:
            assert self.case.fail
            for i in range(4,56):self.memory.pop(self.child_sp+i,None)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=destination(self.case,self.child_sp)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __contains__(self,pc):return pc in self.owner.window_ends or super().__contains__(pc)
    def __getitem__(self,pc):
        if pc in self.owner.window_ends:self.owner.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
