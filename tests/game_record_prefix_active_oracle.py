"""Read-only prefix predicate and the bounded original continuation window."""
from dataclasses import dataclass
from tools.experiments import game_record_prefix_active_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode
OWNER,MARK=0x30000,0x40000
CALLER,CALLER_ROM,END,FOLLOW=0x15096F18,0xC43C8,0x15097588,0x15096A68
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(n&0xFFFFFFFF)-0x100000000 if n&0x80000000 else n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    count:int=3
    hit:int=-1
    value:int=1
    duplicate:bool=False
    phase:int=0
    provider_mode:int=0
    provider_return:int=0
def symbols():return dict(D_800D2DC0=source.TABLE)
def fixture(c=Case(),s=None):
    table=(symbols()if s is None else s)['D_800D2DC0'];m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,768)}
    for base,size in((table,0x24*72),(OWNER,64),(MARK,16)):
        for i in range(size):m[u32(base+i)]=(i*29+0xA5)&255
    for i in range(72):m[u32(table+0x24*i)]=c.value if i==c.hit or(c.duplicate and c.hit>=0 and i>c.hit)else 0
    put(m,OWNER+8,c.count);return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+768}
def reference(m,c=Case(),s=None):
    table=(symbols()if s is None else s)['D_800D2DC0'];count=signed(c.count)
    # Bound the model by the fixture's mapped prefixes, including large-count
    # early returns; never reinterpret a missing read as a semantic mismatch.
    if count<=0:return 0,[]
    loads=[]
    for i in range(count):
        a=u32(table+36*i);value=m[a];loads.append(('R',a,1,value))
        if value:return 1,loads
    return 0,loads
def provider_effect(m,c,s):
    if c.provider_mode&1:put(m,OWNER+8,0x80000000)
    if c.provider_mode&2:m[s['D_800D2DC0']]=255
    if c.provider_mode&4:put(m,MARK,0xDEADBEEF)
class PrefixOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
        self.case=c;self.syms=symbols()if s is None else s
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(u32(c.count),),connected=connected)
        self.trace=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def execute(self,word):
        if word>>26==32:
            self.own_instruction=True
            try:
                imm=word&65535;imm=imm-65536 if imm&32768 else imm
                value=self.get(u32(self.r[word>>21&31]+imm),1);self.r[word>>16&31]=u32((value^128)-128);self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)
    def record_call(self,target):
        assert target in(source.ENTRY,FOLLOW);args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==FOLLOW;provider_effect(self.memory,self.case,self.syms)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.provider_return)
def caller_machine(body,words,c=Case()):
    initial=fixture(c);answer,_=reference(initial,c);expected=dict(initial);calls=[(source.ENTRY,(u32(c.count),))]
    if not answer:calls.append((FOLLOW,(u32(c.count),)));provider_effect(expected,c,symbols())
    code=dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words));code[END]=0
    m=PrefixOracle(body,initial,c,entry=CALLER,connected=code);m.r[16]=OWNER;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
    return m,(expected,calls)
