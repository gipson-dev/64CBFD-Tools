"""Attachment debris: literal byte selectors, live providers and four-entry C domain."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_coordinate_query_result_oracle import trunc
ENTRY,OWNER,ALT,MATRICES,SECOND=0x150EEE00,0x30000,0x31000,0x70000,0x72000
TABLE,MASK,JOINT=0x800A15F0,0x800A163C,0x800A1638
SYMS=dict(func_150EEF80=0x150EEF80,func_15143134=0x15143134,func_150ADA20=0x150ADA20,func_151602C0=0x151602C0,func_150F0A24=0x150F0A24,D_800A15F0=TABLE,D_800A163C=MASK,D_800A1638=JOINT)
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    selector:int=0
    flags:int=0
    base:int=MATRICES
    random:int=0xFFFFFFFF
    mutation:int=0
    phase:int=0
    seed:int=0
    owner:int=OWNER
    results:tuple=(0x3FE00000,0xC1080000,0xBFE00000)

def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def vector(c,home=None):return (STACK+c.phase if home is None else home)-12
def fixture(c,rom):
    m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
    for n,base in enumerate((c.owner,ALT)):
        for i in range(0x240):m[base+i]=(i*29+c.seed*17+n*13+90)&255
        put(m,base+0x94,c.flags);put(m,base+0x1D4,c.base)
    m.update({TABLE+i:b for i,b in enumerate(rom[0x2460B0:0x2470B0])})
    for base in (MATRICES,SECOND):
        for j in range(32):
            for k in range(16):
                value=((j*7+k*3+c.seed)%19-9)*0.25
                if 12<=k<=14:value=j*4+(k-12)*3-c.seed*0.125
                put(m,base+j*64+k*4,bits(value))
    put(m,0x800D154C,c.owner);put(m,0x800D1580,c.selector);m[0x800C3E90]=0
    for a in range(0x800DCA00,0x800DCA20):m[a]=0xA5
    return m

def effect(m,c,stage,home):
    p=home-12
    if stage==0:
        if c.mutation&1:put(m,c.owner+0x1D4,SECOND if c.base else MATRICES)
        if c.mutation&2:put(m,home,ALT)
        if c.mutation&4:put(m,home+7,(c.selector+1)&255,1)
    elif stage==1:
        if c.mutation&32:put(m,c.owner+0x1D4,0)
    elif stage==2:
        if c.mutation&8:
            for j,w in enumerate((0xC29B8000,0x41BF0000,0x3F000001)):put(m,p+j*4,w)
    elif stage==3:
        if c.mutation&16:
            for j,w in enumerate((0x41200000,0xC1200000,0x3F800000)):put(m,p+j*4,w)

def snapshot(m,c,stage,args,home):
    owner=data(m,c.owner,0x240)
    if stage==0:return(stage,args,owner)
    if stage==1:return(stage,args,tuple(read(m,args[0]+j*4)for j in range(3)),owner)
    if stage==2:return(stage,args,data(m,home-20,2),tuple(read(m,home-12+j*4)for j in range(3)),owner)
    if stage==3:return(stage,args,data(m,args[0],6),data(m,args[1],12),tuple(read(m,home-12+j*4)for j in range(3)),owner)
    return(stage,args,tuple(read(m,args[0]+j*4)for j in range(3)),owner)

def reference(initial,c,home=None,s=SYMS):
    home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];snapshots=[]
    put(m,home+4,c.selector);selector=c.selector&255
    if read(m,c.owner+0x94)&read(m,s['D_800A163C']+selector,1):return m,calls,snapshots
    put(m,home,c.owner);put(m,home+7,selector,1)
    def call(stage,name,args):
        calls.append((s[name],args));snapshots.append(snapshot(m,c,stage,args,home))
    call(0,'func_150EEF80',(c.owner,selector,255,1));effect(m,c,0,home)
    owner=read(m,home);selector=read(m,home+7,1);base=read(m,owner+0x1D4)
    if not base:return m,calls,snapshots
    args=(u32(s['D_800A15F0']+selector*12),home-12,u32(base+(read(m,s['D_800A1638']+selector,1)<<6)))
    call(1,'func_15143134',args)
    for j,w in enumerate(c.results):put(m,home-12+j*4,w)
    effect(m,c,1,home);put(m,home-20,3,1);put(m,home-19,255,1)
    call(2,'func_150ADA20',());effect(m,c,2,home)
    put(m,home-18,u32(c.random)%3+4,2);put(m,home-16,0,1)
    for j in range(3):put(m,home-32+j*4,trunc(read(m,home-12+j*4)))
    call(3,'func_151602C0',(home-20,home-32,255,255,255,255,255,0,0,255,1));effect(m,c,3,home)
    call(4,'func_150F0A24',(home-12,))
    return m,calls,snapshots

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,arguments=None):
        self.snapshots=[];self.semantic_home=STACK+c.phase
        super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.owner,u32(c.selector))if arguments is None else arguments)
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==13:
            prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
            try:self.f[w>>6&31]=trunc(self.f[w>>11&31])
            finally:self.own_instruction=prior
        else:super().execute(w)
    def record_call(self,t):
        names=('func_150EEF80','func_15143134','func_150ADA20','func_151602C0','func_150F0A24');stage=next((i for i,n in enumerate(names)if self.syms[n]==t),None)
        assert stage is not None,hex(t);args=tuple(map(u32,self.arguments((4,3,0,11,1)[stage])));self.calls.append((t,args));self.snapshots.append(snapshot(self.memory,self.case,stage,args,self.semantic_home));self.events.append(('CALL',t,args))
    def hook(self,t):
        c=self.case;s=self.syms;stage=next(i for i,n in enumerate(('func_150EEF80','func_15143134','func_150ADA20','func_151602C0','func_150F0A24'))if s[n]==t)
        if stage==1:
            for j,w in enumerate(c.results):put(self.memory,self.calls[-1][1][1]+j*4,w)
        effect(self.memory,c,stage,self.semantic_home)
        for j in range(4):self.put(u32(self.r[29]+j*4),0xB5000000+j,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=u32(c.random)if stage==2 else(0 if stage==0 else 0x87654321)

def cases():
    for selector,phase,flags in itertools.product(range(256),(0,8),(0,0xFFFFFFFF)):
        yield Case(selector=selector,phase=phase,flags=flags,base=MATRICES if selector&1 else 0,mutation=selector&63,seed=selector%3,random=(0,1,2,3,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[selector%7])
    for selector,mutation,phase in itertools.product((0,1,2,3,0xAABBCC00,0x80000003),range(64),(0,8)):
        yield Case(selector=selector,mutation=mutation,phase=phase,random=0xFFFFFFFF,results=(0x7FC01234,0x7F800000,0xCF000000)if mutation&32 else Case.results)
