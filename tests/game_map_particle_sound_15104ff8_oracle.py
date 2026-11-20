"""Independent activation, positional-sound ABI and live source reload model."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,RECORD,FIRST,ALT,REMOVE,START=0x15104FF8,0x30000,0x50000,0x51000,0x1000FD38,0x1000FA64
CALLBACK,REGISTRY,PARENT=0x1000EF40,0x8008A8D8,0x15149434
u32=lambda n:n&0xffffffff
short=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    command:int=0x38
    state:int=1
    mutation:int=0
    coords:tuple=(-32768,0,32767)
    phase:int=0
    alias:int=0
    seed:int=0
def cases():
    for command,state,phase in itertools.product(range(256),(0,1,2,255),(0,8)):
        yield Case(command,state,phase=phase,seed=command&15)
    for mutation,coords,phase,alias in itertools.product(range(8),((-32768,-1,32767),(0,0,0),(123,-456,789)),(0,8),range(3)):
        yield Case(mutation=mutation,coords=coords,phase=phase,alias=alias)
    for command in(0x12345638,0xFFFFFF38,0x80000000,0x12345639):yield Case(command=command)
def source(c):return FIRST if c.alias==0 else RECORD+0x40 if c.alias==1 else RECORD
def fixture(c):
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-512,256)}
    for base in(RECORD,FIRST,ALT):m.update({base+i:(i*29+c.seed+0x5A)&255 for i in range(128)})
    put(m,RECORD+0x28,source(c));put(m,RECORD+0x30,0x8123,2);m[RECORD+0x13]=45
    for base,coords in((source(c),c.coords),(ALT,(32767,-32768,-12345))):
        for i,v in enumerate(coords):put(m,base+2*i,v,2)
        m[base+0x14]=c.state
    return m
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
def effects(m,c):
    if c.mutation&1:put(m,RECORD+0x28,ALT)
    if c.mutation&2:
        for i,v in enumerate((0x8001,0x7FFE,0xFEDC)):put(m,read(m,RECORD+0x28)+2*i,v,2)
    if c.mutation&4:put(m,RECORD+0x30,0xFFFF,2)
def reference(initial,c):
    m=dict(initial);calls=[]
    if c.command&255==0x38:
        p=read(m,RECORD+0x28)
        if m[p+0x14]==1:
            put(m,RECORD+0x30,300,2);calls.append((REMOVE,(CALLBACK,p,0)));effects(m,c)
            p=read(m,RECORD+0x28);xyz=tuple(u32(short(read(m,p+2*i,2)))for i in range(3))
            calls.append((START,(0x236,*xyz,0x4000,1500,1000,CALLBACK,p,0,8,0)))
    return public(m),calls
class Boundary(Exception):pass
class Oracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,arguments=None,fault=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,0xDEADBEEF,c.command)if arguments is None else arguments,connected=connected)
        self.c=c;self.trace=[];self.public_fault=fault;self.public_accesses=0
    def track(self,kind,address,size,value=None):
        if self.own_instruction and not STACK-512<=address<STACK+256:
            if self.public_accesses==self.public_fault:raise Boundary
            self.public_accesses+=1;self.trace.append((kind,address,size,value))
    def get(self,address,size):
        self.track('R',address,size);v=super().get(address,size)
        if self.own_instruction and not STACK-512<=address<STACK+256:self.trace[-1]=('R',address,size,v)
        return v
    def put(self,address,value,size):
        self.track('W',address,size,value&((1<<(size*8))-1));super().put(address,value,size)
    def record_call(self,t):
        assert t in(REMOVE,START,ENTRY),hex(t)
        args=self.arguments(3 if t in(REMOVE,ENTRY)else 12)
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        assert t in(REMOVE,START)
        if t==REMOVE:effects(self.memory,self.c)
        # O32 providers may overwrite their incoming argument homes.
        for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
        for j in(1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
        self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xABCD
def preserved(m,c):
    assert m.r[29]==STACK+c.phase and all(m.r[j]==m.before[j]for j in(*range(16,24),28,30,31))and m.f[20:]==m.saved_f
def guest_checks(truth,raw):
    visited=[set(),set()];count=0
    for c in cases():
        initial=fixture(c);expected=reference(initial,c);traces=[]
        for i,words in enumerate((truth,raw)):
            m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls)==expected,(c,i,m.calls,expected[1]);preserved(m,c)
            visited[i].update(m.visits);traces.append(m.trace)
        assert traces[0]==traces[1],c;count+=1
    assert all(set(range(ENTRY,ENTRY+184,4))<=v for v in visited)
    # A non-activation command must not dereference an absent source pointer.
    c=Case(command=0);m=fixture(c)
    for j in range(4):m.pop(RECORD+0x28+j)
    for words in(truth,raw):assert not Oracle(words,m,c).run().calls
    return dict(cases=count,streams=2,visited_words=46,public_access_order_equal=True,helper_source_reload=True,guest_alias_layouts=3,absent_pointer_lazy_command=True)
def caller_checks(truth,raw,root):
    rom=(root/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>23I',rom,0x1768E4));count=0;visits=set()
    assert struct.unpack_from('>I',rom,0x22F44C)[0]==ENTRY
    for c in[Case(),Case(state=0),Case(command=0),Case(mutation=7),Case(phase=8,mutation=3)]:
        initial=fixture(c);put(initial,REGISTRY+45*4,ENTRY);expected=reference(initial,c)
        for words in(truth,raw):
            connected=dict(zip(range(ENTRY,ENTRY+184,4),words));m=Oracle(parent,initial,c,entry=PARENT,connected=connected).run()
            assert(public(m.memory),m.calls)==(expected[0],[(ENTRY,(RECORD,0xDEADBEEF,c.command&255)),*expected[1]])
            preserved(m,c);visits.update(v for v in m.visits if PARENT<=v<PARENT+92)
        count+=1
    return dict(cases=count,streams=2,original_parent_words=23,visited_parent_words=len(visits),registry=REGISTRY,slot=45,void_return_not_consumed=True,other_slots_not_qualified=True)
def fault_checks(truth,raw):
    count=0
    for c in(Case(),Case(state=0),Case(command=0),Case(mutation=7),Case(alias=1,mutation=3)):
        initial=fixture(c);valid=Oracle(truth,initial,c).run()
        for cut in range(valid.public_accesses):
            observed=[]
            for words in(truth,raw):
                m=Oracle(words,initial,c,fault=cut)
                try:m.run();raise AssertionError('Unfired public access boundary')
                except Boundary:pass
                observed.append((public(m.memory),m.calls,m.trace))
            assert observed[0]==observed[1];count+=1
    return dict(public_access_prefixes=count,streams=2,private_fault_address_identity_not_claimed=True)
