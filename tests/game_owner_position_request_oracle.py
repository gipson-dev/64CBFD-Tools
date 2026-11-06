"""Owner snapshot, live partial records, forward copies and original query/factory."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_owner_position_request_candidates as source
from tools.tests.game_table_payload_spawn_oracle import Oracle as InstructionOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
COPY,QUERY,FACTORY,TRANSFORM,ALLOC,ZERO=0x10022EC0,0x151A4E34,0x15147A80,0x15143134,0x15167A68,0x100226F0
INPUT,ACTOR,MATRICES,OUTPUT=0x30000,0x40000,0x70000,0x50000
SYMS=dict(memcpy=COPY,func_151A4E34=QUERY,func_15147A80=FACTORY)
MASK=0xffffffff
POINTS=((0x3f800000,0x40000000,0xc0400000),(0x80000000,0,0x80000000),(0x7f800000,0x7fc12345,0x7f812345),(1,0x7f7fffff,0x80000001))
@dataclass(frozen=True)
class Case:
    active:bool=True
    query:int=1
    outcome:bool=True
    channel:int=0x123400e1
    mutation:int=0
    phase:int=0
    seed:int=0
    input:int=INPUT
    record:int=OUTPUT
    destination:int|None=None
    points:tuple=POINTS[0]
    slot:int=3
    actor_flags:int=0
    poison:int=0xdeadbeef
def destination(c):return c.record+0xa0 if c.destination is None else c.destination
def homes(c):
    home=STACK+c.phase;sp=home-0xa8
    return home,sp,sp+0x3c,sp+0x8c
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}
def fixture(c=Case()):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2048)}
    for base,n in((c.record-32,0x1a40),(destination(c)-32,0xa0),(ACTOR,0x200),(c.input,0x30)):
        m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
    put(m,c.input,ACTOR if c.active else 0);m[c.input+5]=c.slot&255
    put(m,ACTOR+0x1d4,MATRICES if c.query else 0);m[ACTOR+0x74]=c.actor_flags&255
    return m
def copy_bytes(m,dst,src,n):
    for i in range(n):m[dst+i]=m[src+i]
def scratch(m,sp):
    for i in range(4):put(m,sp+4*i,0xb5000000+i)
def query_effect(m,c):
    home,sp,p,r=homes(c)
    if c.mutation&2:
        m[p+9]^=0x5a;put(m,r+0xe,read(m,r+0xe,2)^0x40,2);m[r+0x15]=c.channel&255
    if c.mutation&4:put(m,home+4,read(m,home+4)^0xff)
def factory_effect(m,c):
    _,_,p,r=homes(c)
    if c.mutation&8:
        m[p+11]^=0xa5;m[p+0x30]=9;put(m,p+0x40,0xbf800000)
        for i,v in enumerate(c.points):put(m,r+4*i,v^0x80000000)
def reference(initial,c=Case(),ra=0xa000001f,connected=False,s=SYMS):
    m=dict(initial);home,sp,p,r=homes(c);calls=[];requests=[];payloads=[]
    put(m,sp+0x34,ra);put(m,home+4,c.channel)
    if read(m,c.input)==0:return m,calls,requests,payloads,0
    calls.append((s['memcpy'],(p,c.input,48)));copy_bytes(m,p,c.input,48)
    if not connected:
        if c.mutation&1:m[c.input+12]^=0x33
        scratch(m,sp)
    m[p+0x44]=0;m[r+0x15]=50;put(m,r+0xe,2,2);put(m,r+0xc,1000,2);m[p+0x30]=6;m[p+0x4c]=0;put(m,p+0x40,0);put(m,p+0x48,0)
    calls.append((s['func_151A4E34'],(p,r)))
    good=bool(c.query)
    if connected:
        owner=read(m,p);target=read(m,owner+0x1d4);good=bool(target)and(m[owner+0x74]&15)!=15
        if good:calls.append((TRANSFORM,(p+8,r,(target+(m[p+5]<<6))&MASK)))
    if not connected or good:
        query_effect(m,c)
        if good:
            for i,v in enumerate(c.points):put(m,r+4*i,v)
    if not connected:scratch(m,sp)
    if good:
        for i in range(3):put(m,p+0x34+4*i,read(m,r+4*i))
        put(m,r+0xe,read(m,r+0xe,2)|4,2)
    put(m,r+0x10,8);channel=m[home+7];a=(r,80,24,6,6,6,0,0,0,channel,0);calls.append((s['func_15147A80'],a));requests.append(data(m,r,28))
    for i,v in enumerate(a[4:]):put(m,sp+16+4*i,v)
    if connected:
        kind=77 if read(m,r+0xe,2)&0x40 else 34
        calls.append((ALLOC,(kind,0,80+m[r+0x15]*24+0xa0,1,channel,1)))
    factory_effect(m,c)
    if c.outcome:
        dst=c.record+0xa0 if connected else destination(c);put(m,c.record+0x98,dst)
        if connected:
            put(m,c.record+0x94,dst+80);calls.append((COPY,(c.record+0x10,r,28)));copy_bytes(m,c.record+0x10,r,28)
            for i,v in enumerate((0,0,0,6,6,6)):m[c.record+0x2c+i]=v
            m[c.record+0x7c]=0;put(m,c.record+0x34,0);put(m,c.record+0x50,0);m[c.record+0x38]=0
            for off in(0x3c,0x40,0x44,0x48,0x4c,0x54,0x58,0x5c):put(m,c.record+off,0)
            calls.append((ZERO,(c.record+0x84,16)))
            for i in range(16):m[c.record+0x84+i]=0
        else:scratch(m,sp)
        dst=read(m,c.record+0x98);put(m,sp+0x38,c.record);calls.append((s['memcpy'],(dst,p,80)));payloads.append(data(m,p,80));copy_bytes(m,dst,p,80)
        if not connected:scratch(m,sp)
        answer=read(m,sp+0x38)
    else:
        if not connected:scratch(m,sp)
        answer=0
    return m,calls,requests,payloads,answer
class Oracle(InstructionOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,s=SYMS,arguments=None):
        self.c=c;self.s=s;self.home,self.sp,self.payload,self.request=homes(c)
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.input,c.channel)if arguments is None else arguments,connected=connected)
        self.requests=[];self.payloads=[];self.trace=[]
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction:self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        counts={source.ENTRY:2,self.s['memcpy']:3,self.s['func_151A4E34']:2,self.s['func_15147A80']:11,TRANSFORM:3,ALLOC:6,ZERO:2}
        if t not in counts:raise AssertionError(('Unbounded owner-request provider',hex(t)))
        a=tuple(v&MASK for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==self.s['func_15147A80']:self.requests.append(data(self.memory,a[0],28))
        if t==self.s['memcpy']and a[2]==80:self.payloads.append(data(self.memory,a[1],80))
    def hook(self,t):
        c=self.c;a=self.calls[-1][1];value=c.poison
        if t==self.s['memcpy']:
            assert a[2]in(28,48,80);copy_bytes(self.memory,*a)
            if a[2]==48 and c.mutation&1:self.memory[c.input+12]^=0x33
        elif t in(self.s['func_151A4E34'],TRANSFORM):
            query_effect(self.memory,c)
            if c.query or t==TRANSFORM:
                for i,v in enumerate(c.points):put(self.memory,self.request+4*i,v)
            value=c.query
        elif t in(self.s['func_15147A80'],ALLOC):
            factory_effect(self.memory,c);value=c.record if c.outcome else 0
            if t==self.s['func_15147A80']and value:put(self.memory,c.record+0x98,destination(c))
        elif t==ZERO:
            assert a[1]==16
            for i in range(a[1]):self.memory[a[0]+i]=0
        else:raise AssertionError(('Unowned owner-request helper',hex(t)))
        scratch(self.memory,self.r[29])
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value&MASK
def helper_code(rom):
    code={}
    for entry,end in((COPY,0x10022eec),(QUERY,0x151a4e9c),(FACTORY,0x15147c4c)):
        at=entry-0x10000000 if entry<0x15000000 else entry-0x15000000+0x2d4b0;n=(end-entry)//4
        code.update(zip(range(entry,end,4),struct.unpack_from('>%dI'%n,rom,at)))
    return code
def cases():
    for active,query,outcome,channel,mutation,phase in itertools.product((False,True),(0,1),(False,True),(0,255,0x12340001,0xffffffff),(0,1,2,4,8,15),(0,8)):
        yield Case(active=active,query=query,outcome=outcome,channel=channel,mutation=mutation,phase=phase)
    for byte in range(256):yield Case(channel=0x12340000|byte,query=byte&1,mutation=2,points=POINTS[byte%4],seed=byte%8)
    for source_addr,dst,mutation in itertools.product((0,STACK,STACK+4,STACK-0x70,STACK-0x68),(STACK-0x70,STACK-0x6c,STACK-0x68,OUTPUT+0x98),(0,2,12)):
        yield Case(input=source_addr,destination=dst,mutation=mutation)
    for point,query,outcome in itertools.product(POINTS,(0,0x80000000),(False,True)):yield Case(points=point,query=query,outcome=outcome)
