"""Independent command/store model; sparse ABI and shift probes remain guest-only."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
ENTRY,TABLE,PAGE=0x1513B83C,0x80089C28,0x800BE9C0
RESOURCE,CURSOR,ALTERNATE,SLOT=0x50000,0x60000,0x70000,0x90000
CALLBACKS=(0x1513B968,0x15108D24,0x1513BAD4,0x151BA084,0x15109120,0x1513BBFC,0x150F2518)
SERVICE=0x150A7B80
u32=lambda v:v&0xFFFFFFFF
signed16=lambda v:((v&65535)^32768)-32768
signed8=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
    flags:int=0
    mask:int=255
    index:int=-1
    view:int=0
    page:int=0
    outcome:int=1
    mutation:int=0
    alias:int=0
    phase:int=0
    seed:int=0
    connected:int=0
    base:int=CURSOR
    resource:int=RESOURCE
def symbols():return dict(D_80089C28=TABLE,D_800BE9C0=PAGE)
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[u32(p+i)]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[u32(p+i)]=b
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def cursor(c):return (c.base,PAGE,PAGE-8,c.resource+0x50,c.resource+0x58)[c.alias]
def callback(c):
    index=signed8(c.index)
    return CALLBACKS[index]if 0<=index<7 else u32(0x16000000+index*4)
def args(c):return tuple(map(u32,(cursor(c),c.resource,c.view)))
def buffer_address(c,page,view):return u32(c.resource+0x58+(page&255)*16+signed16(view)*4)
def fixture(c=Case(),order='big'):
    ranges=((c.resource,8192),(c.base,256),(ALTERNATE,256),(TABLE-512,1024),(PAGE-32,128),(STACK+c.phase-1024,1536))
    sets=[{u32(a+i)for i in range(n)}for a,n in ranges]
    for i,s in enumerate(sets):assert not any(s&t for t in sets[i+1:]),'Guest arenas must be disjoint'
    m={}
    for a,n in ranges:
        for i in range(n):m[u32(a+i)]=(i*29+c.seed*11+90)&255
    m[c.resource+0x10]=c.flags&255;m[c.resource+0x49]=c.mask&255;m[c.resource+0x12]=c.index&255;m[PAGE]=c.page&255
    for i,t in enumerate(CALLBACKS):wr(m,TABLE+i*4,t,4,order)
    wr(m,TABLE+signed8(c.index)*4,callback(c),4,order)
    for page in(c.page,1,0xDA,0xDB):
        for view in(signed16(c.view),2):
            p=buffer_address(c,page,view)
            if not all(u32(p+i)in m for i in range(4)):wr(m,p,0xABCD0000|((page&255)<<8)|(view&255),4,order)
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}
def effect(m,c,order='big',home=None):
    if c.mutation==1:
        m[PAGE]=1;wr(m,buffer_address(c,1,c.view),0x13579BDF,4,order);wr(m,c.resource+0x54,0x2468ACE0,4,order)
    elif c.mutation==2:
        assert home is not None;wr(m,home+10,2,2,order)
    elif c.mutation==3:
        assert home is not None;wr(m,home,ALTERNATE,4,order)
    elif c.mutation==4:m[c.resource+0x12]=255;m[c.resource+0x49]=0
def reference(initial,c=Case(),order='big'):
    m=dict(initial);calls=[];p=cursor(c);view=signed16(c.view);home=STACK+c.phase
    if m[c.resource+0x10]&2 and not(m[c.resource+0x49]&(1<<(view&31))):return dict(memory=m,observed=public(m,c),calls=calls,value=u32(p))
    index=signed8(m[c.resource+0x12])
    if index!=-1:
        t=rd(m,TABLE+index*4,4,order);calls.append((t,(u32(c.resource),u32(view))))
        if c.connected==1:
            assert index==0;calls.append((SERVICE,(u32(c.resource+0x78+m[PAGE]*64),)));result=1
            if c.mutation==1:effect(m,c,order,home)
        elif c.connected==2:assert index==2;result=0
        else:effect(m,c,order,home);result=c.outcome
        if c.mutation==2 and not c.connected:view=2
        if c.mutation==3 and not c.connected:p=ALTERNATE
        if not result:return dict(memory=m,observed=public(m,c),calls=calls,value=u32(p))
    wr(m,p,0xDA380003,4,order)
    wr(m,p+4,c.resource+0x78+m[PAGE]*64,4,order)
    wr(m,p+8,0xDB060004,4,order)
    wr(m,p+12,rd(m,buffer_address(c,m[PAGE],view),4,order),4,order)
    wr(m,p+16,0xDE000000,4,order)
    wr(m,p+20,rd(m,c.resource+0x54,4,order),4,order)
    return dict(memory=m,observed=public(m,c),calls=calls,value=u32(p+24))
def helpers(rom,c):
    locations={1:(CALLBACKS[0],0x168E18,16),2:(CALLBACKS[2],0x168F84,5)};code={}
    if c.connected:
        a,p,n=locations[c.connected];code.update(zip(range(a,a+n*4,4),struct.unpack_from('>%dI'%n,rom,p)))
    return code
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):
        super().__init__(words,memory,c,entry=entry,s=symbols(),connected=connected,arguments=args(c))
    def record_call(self,t):
        n=3 if t==ENTRY else 1 if t==SERVICE else 2
        assert t in(ENTRY,SERVICE,callback(self.case)),hex(t)
        a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        c=self.case
        if t==SERVICE:
            if c.mutation==1:effect(self.memory,c,home=STACK+c.phase)
            value=0x12345678
        else:assert t==callback(c);effect(self.memory,c,home=STACK+c.phase);value=c.outcome
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for flags,mask,index,view,page,outcome in itertools.product((0,2,255),(0,1,128,255),(-1,0,2,6),(0,7,31),(0,1),(0,1)):
        yield Case(flags=flags,mask=mask,index=index,view=view,page=page,outcome=outcome)
    for byte in range(256):yield Case(flags=byte);yield Case(flags=2,mask=byte,view=3)
    for index,view in itertools.product((-128,-2,1,3,4,5,127),(0,0x12340001,0xFFFF8000,0xFFFF)):
        yield Case(index=index,view=view)
    for alias,view,phase in itertools.product((1,2,3,4),(0,2),(0,8)):yield Case(alias=alias,view=view,phase=phase)
    for mutation,outcome,phase in itertools.product(range(1,5),(0,1),(0,8)):yield Case(index=0,mutation=mutation,outcome=outcome,phase=phase)
    for base in(0x7FFFFFF0,0x80000000,0xFFFFFFF0):yield Case(base=base)
