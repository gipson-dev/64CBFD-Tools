"""Reverse queue consumption, live helper mutations and original bounded providers."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_position_queue_drain_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,HELPER,PRODUCER=source.ENTRY,0x1517D074,0x1517D578
PHASE,COUNT,QUEUE,INDEX,PIXEL_GLOBAL=0x800DDD1C,0x8008CEB0,0x800DDD28,0x800DDD58,0x800DDD24
CAPACITY,BUFFERS,VIEW=0x800DDD0C,0x800DDD10,0x800BE9C0
DISPLAY,PIXELS,CURSOR=0x230000,0x240000,0x220000
u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    count:int=3
    cycle:int=0
    pixels:int=PIXELS
    display:int=DISPLAY
    index:int=0x87654321
    mutation:int=0
    returns:int=0
    phase:int=0
    seed:int=0
    connected:int=0
    capacity:int=0
    view:int=0
    stub:int=0

def symbols():return dict(D_800DDD1C=PHASE,D_800DDD58=INDEX,D_8008CEB0=COUNT,D_800DDD28=QUEUE,func_1517D074=HELPER)
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-1024,256)}
    for name,n in(('D_800DDD1C',1),('D_800DDD58',4),('D_8008CEB0',1),('D_800DDD28',48)):
        p=s[name];m.update({p+i:(i*29+c.seed*11+90)&255 for i in range(n)})
    for k in range(3):
        p=s['D_800DDD28']+16*k
        for i,v in enumerate((0x8000+k+c.seed,0x7FFF-k-c.seed,0xFFFF-c.seed)):put(m,p+2*i,v,2)
        m[p+6]=(0,31,255)[(k+c.seed)%3];put(m,p+8,(0,0x8000,0xFFFF)[(k+c.seed)%3],2);put(m,p+10,(65535,1,0x7FFF)[(k+c.seed)%3],2)
        put(m,p+12,(0x80000000,1,0x7F800000,0x7FC12345,0x7FA12345,0xBF800000,0x7F7FFFFF,0)[(k+c.seed)%8])
    m[s['D_800DDD1C']]=c.cycle&255;m[s['D_8008CEB0']]=c.count&255;put(m,s['D_800DDD58'],c.index)
    put(m,CURSOR,c.display);put(m,PIXEL_GLOBAL,c.pixels);put(m,CAPACITY,c.capacity);m[VIEW]=c.view
    for i in range(3):put(m,BUFFERS+4*i,0x300000+0x1000*i)
    return m

def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+256}
def snapshot(m,s):return(m[s['D_800DDD1C']],m[s['D_8008CEB0']],read(m,s['D_800DDD58']),bytes(m[s['D_800DDD28']+i]for i in range(48)))
def returned(a,n,c):
    if c.returns==1:return 0
    if c.returns==2:return 0 if n&1 else c.display
    return u32(a[0]+8*(1+n%3))
def effect(m,c,s,n):
    put(m,s['D_800DDD58'],u32(0xABC00000+n))
    if n==1:
        if c.mutation&1:m[s['D_8008CEB0']]=1
        if c.mutation&2:m[s['D_8008CEB0']]=3
    if c.mutation&4:
        k=n%3;p=s['D_800DDD28']+16*k;m[s['D_800DDD1C']]^=128;m[p+6]=255-n
        put(m,p,u32(0x8000+n),2);put(m,p+8,0xFFF0+n,2);put(m,p+12,0x3F000000+n)
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];obs=[];saved=read(m,s['D_800DDD58']);value=(m[s['D_800DDD1C']]+5)&255;m[s['D_800DDD1C']]=value-200 if value>=200 else value;display=c.display
    while m[s['D_8008CEB0']]:
        index=m[s['D_8008CEB0']]-1;m[s['D_8008CEB0']]=index
        if c.pixels:
            p=u32(s['D_800DDD28']+16*index);a=(display,*[u32(signed16(read(m,p+2*i,2)))for i in range(3)],read(m,p+12),read(m,p+8,2),read(m,p+10,2),16,32,u32(c.pixels+1280*m[p+6]));calls.append((s['func_1517D074'],a));obs.append(snapshot(m,s));n=len(calls)
            if c.stub:display=0
            elif c.connected:
                assert read(m,s['D_800DDD58'])>=c.capacity,'Only the original capacity-reject provider path is connected'
            else:effect(m,c,s,n);display=returned(a,n,c)
            assert n<=4,'Unbounded queue mutation'
    put(m,s['D_800DDD58'],saved);return m,calls,obs,display

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.observations=[];self.root_args=[];self.home=STACK+c.phase;self.n=0
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.display,c.pixels)if arguments is None else arguments)
    def record_call(self,t):
        counts={ENTRY:2,self.s['func_1517D074']:10,PRODUCER:7};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.root_args.append(a);self.home=self.r[29]
        else:self.observations.append(snapshot(self.memory,self.s))
    def hook(self,t):
        assert t==self.s['func_1517D074'];self.n+=1;a=self.calls[-1][1];effect(self.memory,self.case,self.s,self.n);value=returned(a,self.n,self.case)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def helper_code(rom,c):return dict(zip(range(HELPER,HELPER+321*4,4),struct.unpack_from('>321I',rom,0x1AA524)))if c.connected else{}
def cases():
    for cycle,count,pixels in itertools.product(range(256),range(4),(0,PIXELS)):yield Case(cycle=cycle,count=count,pixels=pixels,seed=cycle%8)
    for mutation,count,cycle,returns,phase in itertools.product(range(8),range(4),(0,194,195,250,251,255),range(3),(0,8)):yield Case(mutation=mutation,count=count,cycle=cycle,returns=returns,phase=phase,seed=mutation)
    for count in range(256):yield Case(count=count,pixels=0,cycle=count,index=u32(count*0x1010101))
    for index,display,returns in itertools.product((0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,DISPLAY,0xFFFFFFF0),range(3)):yield Case(index=index,display=display,returns=returns)

def producer(initial,c,args,s=None):
    s=symbols()if s is None else s;m=dict(initial);index=m[s['D_8008CEB0']]
    if index<3:
        p=s['D_800DDD28']+16*index
        for i in range(3):put(m,p+2*i,args[i],2)
        put(m,p+12,args[3]);m[s['D_8008CEB0']]=index+1;put(m,p+8,args[4],2);put(m,p+10,args[5],2);m[p+6]=args[6]&255
    return m
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.observations,m.root_args)
