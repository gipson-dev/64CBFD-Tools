"""Independent byte-state contract, mutable query and original bit helpers."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_actor_state_command_selector_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,QUERY,BITS=source.ENTRY,0x15080738,0x15080718
GLOBAL,PENDING,MASK,BASE,EXISTS=0x800D1940,0x800D199C,0x800D2E60,0x800D3098,0x800BE580
ACTOR,STATE,OTHER,TABLE,MARK=0x30000,0x60000,0x50000,0x80000,0x90000
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
def symbols():return dict(func_15080738=QUERY,D_800D1940=GLOBAL,D_800D199C=PENDING,D_800D2E60=MASK,D_800D3098=BASE)
@dataclass(frozen=True)
class Case:
    command:int=7
    secondary:int=1
    active:int=1
    gate:int=0
    query:int=1
    mask:int=255
    first:int=17
    second:int=19
    record:int=40
    null:bool=False
    mutation:int=0
    phase:int=0
    alias:int=0
    connected:int=0
def args(c):return(0 if c.null else ACTOR,TABLE+c.record*52,u32(c.secondary),u32(c.command))
def state_address(c,s):return(STATE,s['D_800D1940']-0x75,s['D_800D3098']-0x75,ACTOR+0x31C-0x75,ACTOR-0x74)[c.alias]
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase;m={home+i:(i*17+165)&255 for i in range(-512,512)}
    state=state_address(c,s)
    for p,n in((ACTOR,0x32C),(STATE,256),(OTHER,256),(state,256)):
        m.update({u32(p+i):(i*13+89)&255 for i in range(n)})
    for command in(c.command,0xFFFFFFFF):
        index=signed(command)>>3;m[u32(s['D_800D2E60']+index)]=c.mask;m[u32(EXISTS+index)]=255 if c.query else 0
    put(m,MARK,0);put(m,ACTOR,c.active);m[ACTOR+0x127]=c.gate;put(m,s['D_800D3098'],TABLE+36*52);m[s['D_800D1940']]=0xA5;put(m,s['D_800D199C'],0)
    m[state+0x74]=c.first;m[state+0x75]=c.second;put(m,ACTOR+0x31C,state)
    # A status write can redirect the owner's state pointer in this guest alias.
    if c.alias==3:
        for command in(c.command,0x1A,0x2A,0xFFFFFFFF):m[u32((state&0xFFFFFF)|((command&255)<<24))+0x7A]=0xD7
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-512<=p<STACK+c.phase+512}
def effect(m,c,s,home):
    put(m,MARK,0x12345678)
    if c.mutation&1:put(m,ACTOR+0x31C,OTHER);put(m,ACTOR,0);m[ACTOR+0x127]=255
    if c.mutation&2:
        for command in(c.command,0xFFFFFFFF):m[u32(s['D_800D2E60']+(signed(command)>>3))]^=255
    if c.mutation&4:put(m,s['D_800D3098'],TABLE+10*52)
    if c.mutation&8:
        put(m,home+4,TABLE+19*52);put(m,home+8,1);put(m,home+12,0xFFFFFFFF)
def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;m=dict(initial);a,record,secondary,command=args(c);calls=[]
    if not a or not read(m,a)or m[a+0x127]==255:return m,calls
    if command in(0x2B,0x2C):m[s['D_800D1940']]=command;put(m,s['D_800D199C'],record);command=0x2A
    else:
        calls.append((s['func_15080738'],(command,)));effect(m,c,s,home)
        answer=bool(m[u32(EXISTS+(signed(command)>>3))]&(1<<(command&7)))if c.connected else c.query
        if c.mutation&8:record,secondary,command=TABLE+19*52,1,0xFFFFFFFF
        if answer:
            # The availability byte is read before the global command write.
            available=m[u32(s['D_800D2E60']+(signed(command)>>3))]&(1<<(command&7));m[s['D_800D1940']]=command&255
            if not available:command=0x1A
    state=read(m,a+0x31C);offset=0x75 if secondary else 0x74
    if not m[state+offset]&128:
        m[state+offset]=command&255
        if secondary:
            difference=signed(record-read(m,s['D_800D3098']));index=abs(difference)//52*(-1 if difference<0 else 1);m[read(m,a+0x31C)+0x7A]=index&255
    return m,calls
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=args(c)if arguments is None else arguments)
    def record_call(self,t):
        counts={ENTRY:4,self.s['func_15080738']:1,BITS:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t==self.s['func_15080738']:effect(self.memory,self.case,self.s,self.home)
    def hook(self,t):
        assert t==self.s['func_15080738'];value=self.case.query
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helper_code(rom,c):
    code={}
    if c.connected:
        for entry,n in((QUERY,19),(BITS,8)):code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0)))
    return code
def cases():
    for command,secondary,query in itertools.product(range(256),(0,1),(0,1)):
        yield Case(command=command,secondary=secondary,query=query,mask=255 if command&1 else 0,mutation=command%8,phase=(command%2)*8,record=command%73,connected=query)
    for field,byte in itertools.product(('gate','first','second'),range(256)):yield replace(Case(secondary=0 if field=='first'else 1),**{field:byte})
    for command in range(256):
        yield Case(command=command,mask=1<<(command&7))
        yield Case(command=command,mask=255^(1<<(command&7)))
    for command,query in itertools.product((0x100,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0x80000000,0xFFFFFFFF)):yield Case(command=command,query=query,mutation=6)
    for command,secondary,mask in itertools.product((0x2B,0x2C),(0,1,0x80000000),(0,255)):yield Case(command=command,secondary=secondary,mask=mask,mutation=7)
    yield Case(null=True);yield Case(active=0);yield Case(active=0x80000000)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of)
