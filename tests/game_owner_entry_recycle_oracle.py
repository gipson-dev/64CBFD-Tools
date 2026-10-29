"""Independent active/free-chain model and bounded original actor-release execution."""
from dataclasses import dataclass
from tools.experiments import game_owner_entry_recycle_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults

ACTOR,OWNER,TABLE=0x30000,0x31000,0x32000
CALLER,CALLER_ROM,DISPATCH=0x15130A50,0x15DF00,0x80089800
RELEASE,RELEASE_ROM,UNLINK,FALLBACK,OTHER,DESTRUCTOR=0x1516972C,0x196BDC,0x151696DC,0x15169804,0x1510281C,0x15200000
DESTRUCTORS,MARK=0x8008B4D0,0x50000
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:(n&65535)-65536 if n&32768 else n&65535

@dataclass(frozen=True)
class Case:
    length:int=4
    hit:int=2
    free:int=-1
    seed:int=0
    duplicate:bool=False
    phase:int=0
    alias:int=0
    sparse:bool=False
    delta:int=0
    enabled:int=1
    selector:int=0
    kind:int=2
    post_kind:int=-1
    destructor:bool=False

def addresses(c):
    if c.alias==1:return ACTOR,0x80010000,0x8001003C
    if c.alias==2:return OWNER+0x40,OWNER,OWNER+0x40
    return ACTOR+c.delta,OWNER+c.delta,TABLE+c.delta

def indices(c):
    return (-32768,-2,0,32767)[:c.length] if c.sparse else tuple((i*5+c.seed)%13 for i in range(c.length))

def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+768}

def fixture(c=Case()):
    actor,owner,table=addresses(c)
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,768)}
    for base,size in ((actor,0xB0),(owner,0x50),(table,13*8),(MARK,16)):
        for i in range(size):m[u32(base+i)]=(i*29+c.seed+0xA5)&255
    put(m,actor+0xA8,owner);put(m,owner+0x40,table)
    chain=indices(c)
    for j,index in enumerate(chain):
        p=u32(table+index*8)
        for i in range(8):m[u32(p+i)]=(0x81+j*3+i)&255
        matches=j==c.hit or(c.duplicate and j>c.hit>=0)
        put(m,p,actor if matches else actor+0x100+j*0x10)
        put(m,p+4,chain[j+1]if j+1<len(chain)else -1,2)
    put(m,owner+0x44,chain[0]if chain else -1,2);put(m,owner+0x46,c.free,2)
    if c.alias==1:
        # entry[0].next aliases the high halfword of owner.entries. Its link is
        # signed -32767; unlinking the matched entry changes the table pointer.
        put(m,owner+0x40,table);put(m,owner+0x44,0,2);put(m,table,actor+0x100)
        old=u32(table-32767*8);new=u32(0x8002003C-32767*8)
        for p in(old,new):
            for i in range(8):m[p+i]=0xA5
        put(m,old,actor);put(m,old+4,0x8002,2);put(m,new,0x12345678)
    if c.alias==2:
        put(m,owner+0x40,table);put(m,owner+0x44,0,2);put(m,actor+0xA8,owner)
    m[actor]=c.kind;m[actor+0x73]=c.selector&255
    # In alias 2 actor is also entry[0].actor storage: preserve the pointer.
    if c.alias==2:put(m,owner+0x40,table)
    put(m,DISPATCH,source.ENTRY);put(m,DISPATCH+4,OTHER)
    for kind in {c.kind,c.post_kind&255}:
        put(m,DESTRUCTORS+kind*52,DESTRUCTOR if c.destructor else 0)
    return m

def reference(initial,c=Case()):
    m=dict(initial);actor,_,_=addresses(c);owner=read(m,actor+0xA8)
    head=s16(read(m,owner+0x44,2));index=head;previous=None;seen=set()
    while index!=-1:
        if index in seen:raise ValueError('Nonterminating no-match chain')
        seen.add(index);table=read(m,owner+0x40);entry=u32(table+index*8)
        if read(m,entry)==actor:break
        previous=index;index=s16(read(m,entry+4,2))
    if index==-1:return m
    table=read(m,owner+0x40);entry=u32(table+index*8);following=read(m,entry+4,2)
    if previous is None:put(m,owner+0x44,following,2)
    else:
        put(m,u32(table+previous*8+4),following,2)
        entry=u32(read(m,owner+0x40)+index*8)
    put(m,entry+4,read(m,owner+0x46,2),2);put(m,owner+0x46,index,2)
    return m

def effect(m,c,target):
    actor,_,_=addresses(c)
    if target==UNLINK and c.post_kind>=0:m[actor]=c.post_kind
    if target in(FALLBACK,OTHER,DESTRUCTOR):put(m,MARK,{FALLBACK:1,OTHER:2,DESTRUCTOR:3}[target])

def caller_reference(initial,c):
    m=dict(initial);calls=[];actor,_,_=addresses(c)
    def call(target):calls.append((target,(actor,)))
    if c.enabled:
        selector=m[actor+0x73]
        if selector!=255:
            target=read(m,DISPATCH+(selector if selector<128 else selector-256)*4);call(target)
            if target==source.ENTRY:m=reference(m,c)
            else:assert target==OTHER;effect(m,c,target)
        call(RELEASE);call(UNLINK);effect(m,c,UNLINK)
        kind=m[actor]
        if kind>=2:
            target=read(m,DESTRUCTORS+kind*52)or FALLBACK;call(target);effect(m,c,target)
    return m,calls

class RecycleOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None):
        self.case=c
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(addresses(c)[0],),connected=connected)
        self.trace=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def execute(self,word):
        if word>>26==0x20:
            self.own_instruction=True
            try:
                value=self.get(u32(self.r[word>>21&31]+s16(word)),1)
                self.r[word>>16&31]=u32(value-256 if value&128 else value)
            finally:self.own_instruction=False
        else:super().execute(word)
    def record_call(self,target):
        assert target in(source.ENTRY,RELEASE,UNLINK,FALLBACK,OTHER,DESTRUCTOR),('Unbounded recycle provider',hex(target))
        args=self.arguments(1);assert args==(addresses(self.case)[0],),('actor forwarding',target,args)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in(UNLINK,FALLBACK,OTHER,DESTRUCTOR)
        effect(self.memory,self.case,target)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def caller_machine(words,target,release,initial,c):
    connected={source.ENTRY+i*4:w for i,w in enumerate(target)}
    connected.update({RELEASE+i*4:w for i,w in enumerate(release)})
    m=RecycleOracle(words,initial,c,entry=CALLER,connected=connected)
    m.r[7]=c.enabled;m.r[29]-=0x58
    put(m.memory,m.r[29]+0x14,0xDEAD0000);put(m.memory,m.r[29]+0x58,addresses(c)[0])
    return m
