"""Big-endian linked keys, live callback aliases, helper and dispatch windows."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_linked_event_callback_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,HELPER=source.ENTRY,0x151B9660
OWNER,PAIR,TABLE,MARK=0x30000,0x50000,0x800899F8,0x60000
CONSTANTS=(0x800AA56C,0x800AA570)
u32=lambda v:v&0xFFFFFFFF
def symbols():return dict(func_151B9660=HELPER,D_800899F8=TABLE)
@dataclass(frozen=True)
class Case:
    event:int=45
    kind:int=34
    flags:int=256
    index:int=1
    match:int=0
    tag:int=0xA5
    first:int=0x12345678
    second:int=0x87654321
    callback:int=1
    mutation:int=0
    alias:int=0
    phase:int=0
    seed:int=0
def addresses(c,s=None):
    s=symbols()if s is None else s
    owner=(OWNER,OWNER,OWNER,OWNER,s['D_800899F8']-0x7C,s['D_800899F8']-0x60)[c.alias]
    pair=(PAIR,owner+0x7C,owner+0x78,owner+0x60,PAIR,PAIR)[c.alias]
    return owner,pair
def args(c,s=None):return(*addresses(c,s),u32(c.event))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;o,p=addresses(c,s);m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-1024,512)}
    for base,n in((o-32,576),(p-32,64),(s['D_800899F8']-160,1280),(MARK,16)):
        for i in range(n):m[base+i]=(i*29+c.seed*11+90)&255
    for i in range(256):put(m,s['D_800899F8']+4*i,(0x17000000+16*i)if c.callback else 0)
    put(m,o+0x60,c.flags);put(m,o+0x66,c.kind,2);m[o+0x68]=c.index&255
    put(m,p,c.first);put(m,p+4,c.second);m[p+8]=0x38;m[p+9]=0xC7
    put(m,o+0x7C,(c.first,c.second,c.first^0x11223344)[c.match]);m[o+0x80]=c.tag&255
    put(m,MARK,0)
    for a,v in zip(CONSTANTS,(0x3E800000,0xC0200000)):put(m,a,v)
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}
def snapshot(m,o,p):return(bytes(m[o+i]for i in range(0x194)),bytes(m[p+i]for i in range(10)))
def effect(m,c,s,o,p,helper):
    if helper:
        if c.mutation&1:put(m,o+0x60,256);m[o+0x68]=(c.index+1)&255
        if c.mutation&2:put(m,o+0x7C,0xCAFEBABE);m[o+0x80]=0xD1;put(m,p,0xBAD5EED)
        if c.mutation&4:
            for i in range(256):put(m,s['D_800899F8']+4*i,0x18000000+16*i)
        if c.mutation&8:
            put(m,o+0x60,read(m,o+0x60)^256);m[p+9]^=0x55
    else:
        put(m,MARK,read(m,MARK)+1)
        if c.mutation&16:put(m,o+0x7C,0xEEDDCCBB);m[o+0x80]=0x73;put(m,p+4,0x13579BDF)
def helper_writes(m,o):
    for a,v in((0x188,0x40A00000),(0x18C,read(m,CONSTANTS[0])),(0x190,read(m,CONSTANTS[1]))):put(m,o+a,v)
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);o,p=addresses(c,s);event=c.event&255;calls=[];obs=[]
    if event==27 and read(m,o+0x66,2)==34:
        calls.append((s['func_151B9660'],(o,)));obs.append(snapshot(m,o,p));effect(m,c,s,o,p,True);helper_writes(m,o)
    if event==45:
        first,current=read(m,p),read(m,o+0x7C)
        if first==current:put(m,o+0x7C,read(m,p+4));m[o+0x80]=m[p+9]
        elif read(m,p+4)==current:put(m,o+0x7C,first);m[o+0x80]=m[p+8]
    elif event==0:
        if read(m,p)==read(m,o+0x7C)or m[o+0x80]==m[p+4]:put(m,o+0x7C,0);m[o+0x80]=0
    index=m[o+0x68]if read(m,o+0x60)&256 else 0;callback=read(m,s['D_800899F8']+4*index)
    if callback:calls.append((callback,(o,p,event)));obs.append(snapshot(m,o,p));effect(m,c,s,o,p,False)
    return m,calls,obs
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.observations=[];self.root_args=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=args(c,self.s)if arguments is None else arguments)
    def record_call(self,t):
        n=3 if t!=self.s['func_151B9660']else 1;a=tuple(map(u32,self.arguments(n)))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.root_args.append(a);return
        o,p=addresses(self.case,self.s);self.observations.append(snapshot(self.memory,o,p))
        if t==self.s['func_151B9660']:effect(self.memory,self.case,self.s,o,p,True)
    def hook(self,t):
        o,p=addresses(self.case,self.s)
        if t==self.s['func_151B9660']:helper_writes(self.memory,o)
        else:effect(self.memory,self.case,self.s,o,p,False)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xD00DFEED
def helper_code(rom):return dict(zip(range(HELPER,HELPER+44,4),struct.unpack_from('>11I',rom,0x1E6B10)))
def cases():
    for event in range(256):yield Case(event=event,match=event%3,index=event,tag=(event*11)&255,mutation=event&31)
    for event,kind,flags,index,match,tag,callback,phase in itertools.product((0,27,45,0x100,0x11B,0x12D),(0,34,0x8022),(0,256,0xFFFFFEFF),(0,1,5,8,9,255),range(3),(0x87,0xA5),(0,1),(0,8)):
        yield Case(event=event,kind=kind,flags=flags,index=index,match=match,tag=tag,callback=callback,phase=phase)
    for mutation,index in itertools.product(range(32),(0,8,255)):yield Case(event=27,mutation=mutation,index=index)
def semantic_state(m,c):return(public(m.memory,c),m.calls,m.observations,tuple(m.r[i]for i in(*range(16,24),28,29,30)))
def literal_state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.observations)
