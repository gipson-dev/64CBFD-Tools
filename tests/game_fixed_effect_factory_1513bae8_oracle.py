"""Independent descriptor bytes, payload lifetime, original creator/copy/caller."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
ENTRY,CREATE,FREE,COPY=0x1513BAE8,0x1513B5E0,0x1516972C,0x10022EC0
RESOLVE,ALLOCATE,TAIL=0x1502B6BC,0x15167A68,0x1510CE60
CALLER,SETUP,FLAG=0x150E0300,0x1515F170,0x80088980
OUTPUT,ASSET,VIEWS=0x60000,0x80000,0x80082FA0
u32=lambda v:v&0xFFFFFFFF
FIELDS=((0,1,0),(1,1,2),(2,1,5),(4,2,300),(8,4,1),(12,4,0x220205),(16,4,0x40600),(20,4,1),(24,4,54),(28,4,128),(32,4,32),(36,1,0),(37,1,0),(48,4,9),(52,4,430),(56,1,3))
DEFINED=tuple(i for off,n,v in FIELDS for i in range(off,off+n))
PADDING=tuple(i for i in range(60)if i not in DEFINED)
PAYLOAD=(0x3F800000,0x80000000,0x7FC12345,0x7F800000,0xC0200000)
@dataclass(frozen=True)
class Case:
    outcome:int=1
    offset:int=0x1180
    mutation:int=0
    alias:int=0
    phase:int=0
    seed:int=0
    connected:int=0
    views:int=0
    extent:int=2240
    flag:int=0
    base:int=OUTPUT
def symbols():return dict(func_1513B5E0=CREATE,func_1516972C=FREE,memcpy=COPY)
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[u32(p+i)]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[u32(p+i)]=b
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def descriptor(home):return home-64
def payload(home):return home-84
def handle(c,home):return c.base if not c.alias else u32(payload(home)+(0,0,4,20)[c.alias]-0x1278)
def fixture(c=Case(),order='big'):
    regions=((OUTPUT-64,8192),(ASSET-64,2400),(STACK+c.phase-1024,1536))
    for i,(a,n)in enumerate(regions):
        for b,k in regions[i+1:]:assert a+n<=b or b+k<=a,'Guest arenas must remain disjoint'
    m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-1024,512)}
    for p,n in((OUTPUT-64,8192),(ASSET-64,2400),(VIEWS,4),(FLAG,4)):
        for i in range(n):m[p+i]=(i*29+c.seed*11+90)&255
    wr(m,VIEWS,c.views,4,order);wr(m,ASSET,ASSET+40+c.extent,4,order);m[FLAG]=c.flag
    for i in range(4):m[u32(handle(c,STACK+c.phase)+0x50+i)]=0xA5
    if c.base!=OUTPUT:
        for i in range(20):m[u32(c.base+0x1278+i)]=0xA5
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}
def observe(m,c,home=None):
    home=STACK+c.phase if home is None else home
    return public(m,c),data(m,payload(home),80)if c.alias else b''
def mutate(m,c,home,order='big'):
    if c.mutation&1:
        for i,v in enumerate(PAYLOAD):wr(m,payload(home)+4*i,v,4,order)
    if c.mutation&2:
        for off,n,v in FIELDS:wr(m,descriptor(home)+off,v^0x55,n,order)
def reference(initial,c=Case(),home=None,order='big'):
    home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];packets=[]
    for i in range(5):wr(m,payload(home)+4*i,0,4,order)
    for off,n,v in FIELDS:wr(m,descriptor(home)+off,v,n,order)
    def call(t,args):
        calls.append((t,tuple(map(u32,args))))
        if t==CREATE:packets.append((t,data(m,args[0],60),data(m,payload(home),20)))
        if t==COPY:packets.append((t,args[0],data(m,args[1],args[2])))
    def copy(dest,src,n):
        call(COPY,(dest,src,n))
        for i in range(n):m[u32(dest+i)]=m[u32(src+i)]
    call(CREATE,(descriptor(home),1,20,255,1));result=handle(c,home)if c.outcome else 0
    if c.connected&1:
        call(RESOLVE,(home-144,0,home-148,2,9,430))
        total=2*c.extent*(c.views+1)
        call(ALLOCATE,(0x54,1,total+268,2,255,1))
        if result:
            copy(result+16,descriptor(home),60);wr(m,result+0x4C,ASSET,4,order)
            for i in range(c.views+1):
                dest=result+248+2*c.extent*i
                wr(m,result+0x58+4*i,dest,4,order);wr(m,result+0x68+4*i,dest+c.extent,4,order)
                copy(dest,ASSET+40,c.extent);copy(dest+c.extent,ASSET+40,c.extent)
            wr(m,result+0x54,ASSET+40+c.extent,4,order);wr(m,result+0x50,total,4,order)
            call(TAIL,(ASSET+40+c.extent,0,1,62,0))
    else:
        mutate(m,c,home,order)
        if result:wr(m,result+0x50,c.offset,4,order)
    value=result
    if result:
        if rd(m,result+0x50,4,order)!=0x1180:call(FREE,(result,))
        else:copy(u32(result+rd(m,result+0x50,4,order)+248),payload(home),20)
        if c.mutation&8:value=0xBAD01234
    return dict(memory=m,observed=observe(m,c,home),calls=calls,packets=packets,value=u32(value))
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):
        self.home=STACK+c.phase;self.packets=[]
        super().__init__(words,memory,c,entry=entry,s=symbols(),connected=connected,arguments=())
    def record_call(self,t):
        counts={ENTRY:0,CREATE:5,FREE:1,COPY:3,RESOLVE:6,ALLOCATE:6,TAIL:5,SETUP:2}
        assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==ENTRY:self.home=self.r[29]
        if t==CREATE:self.packets.append((t,data(self.memory,args[0],60),data(self.memory,payload(self.home),20)))
        if t==COPY:self.packets.append((t,args[0],data(self.memory,args[1],args[2])))
    def hook(self,t):
        c=self.case;args=self.calls[-1][1];value=0xA5000002
        if t==CREATE:
            mutate(self.memory,c,self.home);value=handle(c,self.home)if c.outcome else 0
            if value:wr(self.memory,value+0x50,c.offset)
        elif t==RESOLVE:
            wr(self.memory,args[0],0x12345678);wr(self.memory,args[2],0x87654321);value=ASSET
        elif t==ALLOCATE:value=OUTPUT if c.outcome else 0
        elif t==COPY:
            for i in range(args[2]):self.memory[u32(args[0]+i)]=self.memory[u32(args[1]+i)]
            value=args[0]
        elif t in(FREE,TAIL,SETUP):pass
        else:raise AssertionError(hex(t))
        if t in(FREE,COPY)and c.mutation&8:wr(self.memory,self.home-4,0xBAD01234)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helpers(rom,c):
    code={}
    for entry,offset,n in(((CREATE,0x168A90,110),)if c.connected&1 else())+(((COPY,0x22EC0,11),)if c.connected&2 else()):
        code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.packets,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for outcome,offset,mutation,phase,seed in itertools.product((0,1),(0x1180,0,0x1181,0xFFFFFFFF,0x80000000),(0,1,2,3,8,11),(0,8),range(3)):
        yield Case(outcome=outcome,offset=offset,mutation=mutation,phase=phase,seed=seed)
    for alias,mutation,connected,phase in itertools.product((1,2,3),(0,1,3),(0,2),(0,8)):
        yield Case(alias=alias,mutation=mutation,connected=connected,phase=phase)
    for base,offset,mutation,phase in itertools.product((0x7FFFFFF0,0x80000000,0xFFFFF000,0xFFFFFFF0,0x10000),(0,0x1180),(0,1),(0,8)):
        yield Case(base=base,offset=offset,mutation=mutation,phase=phase)
