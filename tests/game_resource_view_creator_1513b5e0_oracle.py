"""Independent resource/view byte model; private stack interventions are guest only."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
ENTRY,RESOLVE,ALLOCATE,COPY,TAIL=0x1513B5E0,0x1502B6BC,0x15167A68,0x10022EC0,0x1510CE60
OUTPUT,ASSET,DESC,ALT,VIEWS=0x60000,0x80000,0xA0000,0xC0000,0x80082FA0
REGIONS=((OUTPUT,16384),(ASSET,8192),(DESC,128),(ALT,4096))
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000

@dataclass(frozen=True)
class Case:
    outcome:int=1
    mode:int=1
    priority:int=255
    extra:int=20
    context:int=1
    views:int=0
    extent:int=64
    mutation:int=0
    phase:int=0
    seed:int=0
    alias:int=0
    base:int=OUTPUT
    asset:int=ASSET

def symbols():return dict(func_1502B6BC=RESOLVE,D_80082FA0=VIEWS,func_15167A68=ALLOCATE,memcpy=COPY,func_1510CE60=TAIL)
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[u32(p+i)]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[u32(p+i)]=b
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def desc(c):return (DESC,u32(c.base+16),u32(c.asset+40))[c.alias]
def args(c):return tuple(map(u32,(desc(c),c.mode,c.extra,c.priority,c.context)))
def regions(c):return((c.base,16384),(c.asset,8192),(DESC,128),(ALT,4096))
def fixture(c=Case(),order='big'):
    rr=regions(c)
    # Full-word sparse/wrapped addresses are guest-only. Ordinary regions and
    # all native arenas remain disjoint; no accidental stack/allocation alias.
    sets=[{u32(a+i)for i in range(n)}for a,n in rr]
    for i,ss in enumerate(sets):
        assert not any(ss&other for other in sets[i+1:])
        assert not any(STACK+c.phase-1024<=p<STACK+c.phase+512 for p in ss)
    m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-1024,512)}
    for a,n in rr:
        for i in range(n):m[u32(a+i)]=(i*29+c.seed*11+90)&255
    wr(m,VIEWS,c.views,4,order);wr(m,c.asset,c.asset+40+c.extent,4,order)
    return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+512}

def effect(m,c,t,args,number,order='big',home=None):
    if c.mutation==1 and t==RESOLVE:
        wr(m,desc(c)+48,0x11223344,4,order);wr(m,desc(c)+52,0x55667788,4,order)
    elif c.mutation==2 and t==ALLOCATE:wr(m,VIEWS,1,4,order)
    elif c.mutation==3 and t==COPY and number==1:wr(m,VIEWS,1,4,order)
    elif c.mutation==4 and t==COPY and number==2:
        wr(m,c.base+0x68,ALT,4,order);wr(m,c.asset,c.asset+44+c.extent,4,order)
    elif c.mutation==5 and t==COPY and number==3:wr(m,VIEWS,0,4,order)
    elif c.mutation==6 and t==TAIL:wr(m,c.base+0x50,0xFEED1234,4,order)
    elif c.mutation==7 and t==RESOLVE:
        assert home is not None
        wr(m,home+4,0x10203000,4,order);wr(m,home+12,0x20304000,4,order);wr(m,home+16,0x76543210,4,order)
    elif ((c.mutation==8 and t==ALLOCATE)or(c.mutation==9 and t==COPY and number==1)):
        assert home is not None
        wr(m,home-40,2*c.extent+4,4,order)

def reference(initial,c=Case(),order='big'):
    m=dict(initial);calls=[];packets=[];copies=0;home=STACK+c.phase
    def call(t,arguments):
        nonlocal copies
        arguments=tuple(map(u32,arguments));calls.append((t,arguments))
        if t==COPY:
            copies+=1;d,s,n=arguments;packets.append((d,data(m,s,n)))
            for i in range(n):m[u32(d+i)]=m[u32(s+i)]
        effect(m,c,t,arguments,copies,order,home)
    call(RESOLVE,(home-24,0,home-28,2,rd(m,desc(c)+48,4,order),rd(m,desc(c)+52,4,order)))
    size=u32(rd(m,c.asset,4,order)-c.asset-40)
    step=u32(size*2);total=u32(step*u32(rd(m,VIEWS,4,order)+1))
    context=0x76543210 if c.mutation==7 else c.context
    call(ALLOCATE,(0x54 if c.mode&255 else 0x38,context,u32(c.extra+total+248),2,c.priority&255,1))
    if not c.outcome:return dict(memory=m,observed=public(m,c),calls=calls,packets=packets,value=0)
    call(COPY,(c.base+16,desc(c),60));wr(m,c.base+0x4C,c.asset,4,order)
    if c.mutation in(8,9):step=u32(2*size+4)
    row=c.base;cursor=u32(c.base+248);index=0
    if signed(u32(rd(m,VIEWS,4,order)+1))>0:
        while True:
            assert index<8,'Model fixture exceeds bounded view capacity'
            wr(m,row+0x58,cursor,4,order);wr(m,row+0x68,cursor+size,4,order)
            call(COPY,(cursor,c.asset+40,size))
            call(COPY,(rd(m,row+0x68,4,order),c.asset+40,size))
            row=u32(row+4);cursor=u32(cursor+step);index=u32(index+1)
            if signed(index)>signed(rd(m,VIEWS,4,order)):break
    end=rd(m,c.asset,4,order);wr(m,c.base+0x54,end,4,order);wr(m,c.base+0x50,total,4,order)
    call(TAIL,(end,0,1,62,0))
    return dict(memory=m,observed=public(m,c),calls=calls,packets=packets,value=u32(c.base))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),connected=None):
        self.packets=[];self.copies=0
        super().__init__(words,memory,c,entry=ENTRY,s=symbols(),connected=connected,arguments=args(c))
    def record_call(self,t):
        counts={RESOLVE:6,ALLOCATE:6,COPY:3,TAIL:5};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==COPY:self.packets.append((a[0],data(self.memory,a[1],a[2])))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xABCD0002
        if t==RESOLVE:
            wr(self.memory,a[0],0x12345678);wr(self.memory,a[2],0x87654321);value=c.asset
        elif t==ALLOCATE:value=c.base if c.outcome else 0
        elif t==COPY:
            self.copies+=1
            for i in range(a[2]):
                target=u32(a[0]+i);assert target in self.memory,('unmapped-copy-write',hex(target))
                self.memory[target]=self.memory[u32(a[1]+i)]
            value=a[0]
        elif t!=TAIL:raise AssertionError(hex(t))
        effect(self.memory,c,t,a,self.copies,home=STACK+c.phase)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.packets,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for outcome,views,extent,seed in itertools.product((0,1),(-2,-1,0,1,2),(0,4,64,1120),range(2)):
        yield Case(outcome=outcome,views=views,extent=extent,seed=seed)
    for mode,priority,extra,context in zip((0,0x100,0xFFFFFFFF,0x12340080),(0,0x100,0xFFFF0081,0xFFFFFFFF),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0xFFFFFFFF,0x80000000,0,0x12345678)):
        for phase in(0,8):yield Case(mode=mode,priority=priority,extra=extra,context=context,phase=phase)
    for mutation,views,phase in itertools.product(range(1,8),(0,2),(0,8)):
        yield Case(mutation=mutation,views=views,phase=phase)
    for views in(0x7FFFFFFF,0x80000000,0xFFFFFFFF):yield Case(views=views)
    for alias in(1,2):yield Case(alias=alias)
    for base,asset in((0x7FFFFFF0,ASSET),(0x80000000,ASSET),(0xFFFFFFF0,ASSET),(OUTPUT,0xFFFFFFF0)):
        yield Case(base=base,asset=asset)
