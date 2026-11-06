"""Partial request fields, live argument homes and bounded original effect factory."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_five_source_effect_candidates as source
from tools.tests.game_table_payload_spawn_oracle import Oracle as InstructionOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
FACTORY,CORE,ALLOC,COPY,ZERO,INIT,CONFIG=0x1513D524,0x1513D2F0,0x15167A68,0x10022EC0,0x100226F0,0x1513FFF4,0x151400D0
TABLE,FACTOR,OUTPUT,POINTERS=0x800A4AA0,0x800A5184,0x50000,(0x30000,0x30010,0x30018,0x3001C,0x30020)
MASK=0xffffffff
half=lambda v:((v&65535)^32768)-32768
DEFINED=(0,2,3,4,5,*range(8,20),*range(64,70))
@dataclass(frozen=True)
class Case:
    mask:int=31
    duration:int=1
    channel:int=0xe1
    context:int=0x87654321
    outcome:bool=True
    mutation:int=0
    phase:int=0
    output:int=OUTPUT
    pointers:tuple=POINTERS
    seed:int=0
def args(c):return tuple((p if c.mask>>i&1 else 0)&MASK for i,p in enumerate(c.pointers))+(c.duration&MASK,c.channel&MASK,c.context&MASK)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}
def fixture(c=Case()):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2048)}
    m.update({c.output+i:(i*29+c.seed*11+0x5a)&255 for i in range(-32,0x144)})
    put(m,FACTOR,0x3f4ccccd)
    for i,v in enumerate(args(c)[4:]):put(m,STACK+c.phase+16+4*i,v)
    return m
def initialize_request(m,p,duration):
    m[p]=23;put(m,p+2,0x401,2);put(m,p+4,duration,2);put(m,p+8,0);put(m,p+12,0x243a)
    for i in range(16,20):m[p+i]=200
    put(m,p+64,0x401);m[p+68]=255;m[p+69]=255
def effects(m,c,home,packet):
    if c.mutation&1:
        for i in range(5):put(m,home+4*i,0x31000+i*20)
    if c.mutation&2:m[packet]^=0x55;put(m,packet+4,0xabcd,2);m[packet+0x46]^=0xa5
def scribble(m,sp):
    for i in range(4):put(m,sp+4*i,0xb5000000+i)
def reference(initial,c=Case(),ra=0xa000001f,connected=False,factory=FACTORY):
    m=dict(initial);home=STACK+c.phase;sp=home-0x90;packet=sp+0x38;a=args(c);calls=[];packets=[]
    put(m,sp+0x2c,ra)
    for i,v in enumerate(a[:4]):put(m,home+4*i,v)
    if not all(a[:5])or not half(a[5]):return m,calls,packets
    initialize_request(m,packet,a[5]);call=(packet,0,10,0,8,0,20,a[6]&255,a[7]);calls.append((factory,call));packets.append(data(m,packet,88))
    for i,v in enumerate(call[4:]):put(m,sp+16+4*i,v)
    if connected:
        calls.append((CORE,(packet,TABLE,0,10,0,8,0,0,0,20,a[6]&255,a[7])))
        calls.append((ALLOC,(28,a[7],0x124,1,a[6]&255,1)))
    effects(m,c,home,packet)
    if connected and c.outcome:
        calls.append((COPY,(c.output+24,packet,88)))
        for i,v in enumerate(data(m,packet,88)):m[c.output+24+i]=v
        for i,v in enumerate((0,10,0,8,0)):m[c.output+0x70+i]=v
        calls.append((ZERO,(c.output+0x100,16)))
        for i in range(16):m[c.output+0x100+i]=0
        calls.append((INIT,(c.output+0xc0,m[c.output+24],0)))
        calls.append((CONFIG,(c.output+0xc0,TABLE)))
        for off,v in((0x10,1),(0x14,0),(0x78,read(m,FACTOR)),(0x98,0),(0x90,0),(0x9c,0),(0xb8,0),*( (off,0)for off in(0xa4,0xa8,0xac,0xb0,0xb4))):put(m,c.output+off,v)
        for off in(0x74,0x95,0x94,0xa0):m[c.output+off]=0
    if not connected:scribble(m,sp)
    if c.outcome:
        for off,index in((0x110,0),(0x114,1),(0x118,2),(0x11c,4),(0x120,3)):put(m,c.output+off,read(m,home+4*index))
    return m,calls,packets
class Oracle(InstructionOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,factory=FACTORY):
        self.c=c;self.home=STACK+c.phase;self.packet=self.home-0x58;self.factory=factory
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=args(c)if arguments is None else arguments,connected=connected)
        self.packets=[];self.trace=[]
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction:self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        counts={source.ENTRY:8,self.factory:9,CORE:12,ALLOC:6,COPY:3,ZERO:2,INIT:3,CONFIG:2}
        if t not in counts:raise AssertionError(('Unbounded effect provider',hex(t)))
        a=tuple(v&MASK for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==self.factory:self.packets.append(data(self.memory,a[0],88))
    def hook(self,t):
        a=self.calls[-1][1];value=0xdeadbeef
        if t in(self.factory,ALLOC):effects(self.memory,self.c,self.home,self.packet);value=self.c.output if self.c.outcome else 0
        elif t==COPY:
            assert a[2]==88
            for i,v in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=v
            value=a[0]
        elif t==ZERO:
            assert a[1]==16
            for i in range(a[1]):self.memory[a[0]+i]=0
        elif t not in(INIT,CONFIG):raise AssertionError(('Unowned effect helper',hex(t)))
        scribble(self.memory,self.r[29])
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value&MASK
def helper_code(rom):
    code={}
    for entry,end in((FACTORY,0x1513D594),(CORE,0x1513D4B8)):
        n=(end-entry)//4;at=entry-0x15000000+0x2d4b0
        code.update(zip(range(entry,end,4),struct.unpack_from('>%dI'%n,rom,at)))
    return code
def cases():
    for mask,duration,outcome,mutation,phase in itertools.product(range(32),(0,1,0xffff,0x8000,0x10000,0x12340001),(False,True),(0,1),(0,8)):
        yield Case(mask=mask,duration=duration,outcome=outcome,mutation=mutation,phase=phase)
    for value,duration in itertools.product(range(256),(1,0xffff,0x8000)):
        yield Case(duration=duration,channel=0x87650000|value,context=(0,0x7fffffff,0x80000000,0xffffffff)[value%4],mutation=value&3,seed=value&7)
    for field,value in itertools.product(range(5),(0,1,0xffffffff,0x80000001,0x1234abcd)):
        p=list(POINTERS);p[field]=value;yield Case(pointers=tuple(p))
    for offset,mutation,duration,outcome in itertools.product((0,4,8,12,16,20),(0,1,2,3),(1,0xffff,0x8000),(False,True)):
        yield Case(output=STACK-0x110+offset,mutation=mutation,duration=duration,outcome=outcome)
    for seed,phase,outcome in itertools.product(range(16),(0,8),(False,True)):yield Case(seed=seed,phase=phase,outcome=outcome)
