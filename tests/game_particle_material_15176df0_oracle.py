"""Independent material renderer model, matrix packets and live palette reads."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_particle_material_15176df0_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
RECORD,COMMANDS,MARK,SYNC,TRACK=0x50000,0x60000,0x70000,0x72000,0x71000
EULER,MULTIPLY,MATRIX,MATERIAL,CULL=0x150a8050,0x150a7a48,0x150a7790,0x15142fbc,0x1510aee0
MODELS,LISTS,CONTROL,KINDS,PAGE,STEP=0x800dde80,0x800dde8c,0x800ddf78,0x800a7170,0x800be9c0,0x800be9e4
u32=lambda x:x&0xffffffff
half=lambda x:((x&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    variant:int=0
    present:int=1
    enabled:int=1
    current:int=40
    target:int=84
    step:int=1
    scale:int=0x3f000000
    page:int=0
    mutation:int=0
    phase:int=0
    alias:int=0
    seed:int=0
    view:int=1
    private_colors:bool=False
    reject:int=0

def commands(c):return (COMMANDS,RECORD+0xd0,MODELS-8)[c.alias]
def args(c):return commands(c),RECORD,u32(c.view)
def home(c):return STACK+c.phase
def matrices(h):return h-0x84,h-0x44
def color_words(c):return 0x87654321^c.seed,0x12345678+c.seed,0xffff0000+c.seed

def cases():
    relations=((0,0),(0,255),(1,42),(40,84),(84,42),(127,127),(255,1),(255,255))
    for i,(present,enabled,relation,step,mode,phase) in enumerate(itertools.product((0,1),(0,1),relations,(0,1,17,-1),(0,1,3),(0,8))):
        yield Case(variant=(0,1,3,255)[i//3%4],present=present,enabled=enabled,current=relation[0],target=relation[1],step=step,scale=(0,0x80000000,0xbf800000,0x3f000000,0x7f7fffff)[i%5],page=(0,1,255)[i//5%3],mutation=mode,phase=phase,alias=i%3,seed=i%17)
    for v in range(256):yield Case(variant=v,current=v,target=255-v,step=(0x1fffffff,0x20000000,0x3fffffff,0x40000000,0x80000000)[v%5],seed=v,phase=8*(v&1))

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,768)}
    m.update({RECORD+i:(i*29+c.seed*11+0x59)&255 for i in range(272)})
    m.update({COMMANDS+i:0xa5 for i in range(256)})
    m.update({MODELS+i:0x5a for i in range(-32,5200)})
    for i in range(256):put(m,MODELS+i*20,0x81230000+i*256+c.seed);put(m,LISTS+i*20,0x82340000+i*256+c.seed)
    for i in range(256):put(m,CONTROL+i*4,1)
    put(m,MODELS+c.variant*20,0x81234567 if c.present else 0);put(m,CONTROL+c.variant*4,c.enabled)
    m[RECORD+0xed]=c.variant;m[RECORD+0xec]=c.current;m[RECORD+0xf0]=(c.seed*13+17)&255;m[RECORD+0x91]=1+(c.seed%3)
    for i,off in enumerate((0x98,0x9c,0xa0,0xa8,0xac,0xb0)):put(m,RECORD+off,(0x3f800000,0xbf800000,0x80000000,0x3f4ccccd)[(c.seed+i)%4])
    put(m,RECORD+0x94,0x83450000+c.seed);put(m,RECORD+0xc0,c.scale);put(m,RECORD+0xe8,((c.seed&3)<<5)|0x100)
    for i in range(4):m[KINDS+i]=(0,42,84,127)[i]
    m[KINDS+(c.seed&3)]=c.target;m[PAGE]=c.page;put(m,STEP,u32(c.step));put(m,MARK,0)
    for i,v in enumerate(args(c)):put(m,home(c)+4*i,v)
    for i,a in enumerate((0x800d9b20,0x800d35e0,0x800d35e4)):put(m,a,(0x3f4ccccd,0xbf000000,0x80000000)[i])
    return m

def effects(m,c,t,a,n,h):
    put(m,MARK,u32(t^n*0x1020304))
    if t==EULER:
        for i in range(16):put(m,a[0]+4*i,0x3e800000|((a[1+i%3]+i*0x1111+n*256)&0x7fffff))
    elif t==MULTIPLY:
        left=[read(m,a[0]+4*i) for i in range(16)];right=[read(m,a[1]+4*i) for i in range(16)]
        for i in range(16):put(m,a[2]+4*i,0x3e000000|((left[i]^right[(i+5)%16])&0x7fffff))
    elif t==MATRIX:
        for i in range(64):m[a[1]+i]=(i*7+n*3+c.seed)&255
    elif t==MATERIAL:
        put(m,a[0],0xf1000000|n);put(m,a[0]+4,0x12340000|n);m[a[3]]=0x5a
        if c.private_colors:
            for i,v in enumerate(color_words(c)):put(m,h-0xd8+0x48+4*i,v)
    if c.mutation&1:
        m[PAGE]^=1;m[RECORD+0xed]=(c.seed+n)%4;m[RECORD+0xec]=(c.seed+n*17)&255;m[RECORD+0xf0]=(c.seed+n*31)&255
        m[RECORD+0x91]=1+(c.seed+n)%3
        for i,off in enumerate((0x98,0x9c,0xa0,0xa8,0xac,0xb0)):put(m,RECORD+off,0x3f800000+(n*8+i)*0x10000)
        put(m,RECORD+0x94,0x84560000+n);put(m,RECORD+0xc0,(0xbf000000,0x3e800000,0x40000000)[n%3]);put(m,RECORD+0xe8,(n&3)<<5)
        for i in range(256):put(m,MODELS+i*20,0x85670000+n*256+i);put(m,LISTS+i*20,0x86780000+n*256+i)
        for i in range(4):m[KINDS+i]=(n*17+i*31)&255
        put(m,STEP,n+1)
    if c.mutation&2:put(m,h+8,0x87650000|((n+2)&3))

def observation(m,t,a,h,raw=False):
    if t==MULTIPLY:return tuple(read(m,p+4*i) for p in a[:2] for i in range(16))
    if t==MATRIX:return tuple(read(m,a[0]+4*i) for i in range(16))
    if t==MATERIAL:return tuple(read(m,h-0xd8+(0x40 if raw else 0x48)+4*i) for i in range(3))+(m[a[3]],)
    return ()

def reference(initial,c,h=None,prefix=(),observations=()):
    m=dict(initial);h=home(c) if h is None else h;calls=list(prefix);obs=list(observations);cursor=commands(c)
    def call(t,*a):
        a=tuple(map(u32,a));calls.append((t,(*a[:3],SYNC) if t==MATERIAL else a))
        if t==MATERIAL:obs.append((u32(value),u32(value),u32(value),0))
        else:obs.append(observation(m,t,a,h))
        effects(m,c,t,a,len(calls),h)
        return a[0]+8*(1+c.seed%2) if t==MATERIAL else 0xdeadbeef
    variant=m[RECORD+0xed]
    if not read(m,MODELS+variant*20) or not read(m,CONTROL+variant*4):return m,calls,obs,cursor
    matrix,tilt=matrices(h)
    call(EULER,matrix,0,read(m,RECORD+0xac),0);call(EULER,tilt,read(m,RECORD+0xa8),0,read(m,RECORD+0xb0));call(MULTIPLY,tilt,matrix,matrix)
    for i,off in enumerate((0x98,0x9c,0xa0)):put(m,matrix+48+4*i,read(m,RECORD+off))
    for i in (0,1,2,4,5,6,8,9,10):put(m,matrix+4*i,bits(floating(read(m,matrix+4*i))*floating(read(m,RECORD+0xc0))))
    call(MATRIX,matrix,RECORD+m[PAGE]*64+16)
    put(m,cursor,0xda380003);put(m,cursor+4,RECORD+m[PAGE]*64+16);cursor+=8
    put(m,cursor,0xdb060004);put(m,cursor+4,read(m,RECORD+0x94));cursor+=8
    put(m,cursor,0xe7000000);put(m,cursor+4,0);cursor+=8
    value=m[RECORD+0xec];target=m[KINDS+(read(m,RECORD+0xe8)>>5&3)]
    if value!=target:
        delta=u32(read(m,STEP)<<2)
        if value<target:value=signed(u32(value+delta));value=target if value>target else value
        else:value=signed(u32(value-delta));value=0 if value<0 else value
        m[RECORD+0xec]=value&255
    sync=h-0xd8+0x33;m[sync]=0;cursor=call(MATERIAL,cursor,0x82ca0,0x504a50,sync)
    colors=color_words(c) if c.private_colors else (value,value,value)
    put(m,cursor,0xfb000000);put(m,cursor+4,u32((colors[0]<<24)|((colors[1]&255)<<16)|((colors[2]&255)<<8)|m[RECORD+0xf0]));cursor+=8
    put(m,cursor,0xde000000);put(m,cursor+4,read(m,LISTS+m[RECORD+0xed]*20));cursor+=8
    return m,calls,obs,u32(cursor)

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        super().__init__(words,initial,c,entry=entry,arguments=args(c),connected=connected)
        self.raw=len(words)==181;self.observations=[];self.before_r,self.before_f=self.r[:],self.f[:];self.sync=0;self.entered=home(c)
    def record_call(self,t):
        if t==source.ENTRY:self.entered=self.r[29];return
        a=tuple(map(u32,self.arguments({EULER:4,MULTIPLY:3,MATRIX:2,MATERIAL:4}[t])))
        self.observations.append(observation(self.memory,t,a,self.entered,self.raw))
        if t==MATERIAL:self.sync=a[3];a=(*a[:3],SYNC)
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        a=self.calls[-1][1]
        if t==MATERIAL:a=(*a[:3],self.sync)
        effects(self.memory,self.case,t,a,len(self.calls),self.entered)
        value=a[0]+8*(1+self.case.seed%2) if t==MATERIAL else 0xdeadbeef
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+768}
def verify(m,initial,c,h=None):
    want,calls,obs,result=reference(initial,c,h)
    assert (public(m.memory),m.calls,m.observations,m.r[2])==(public(want),calls,obs,result),c
    assert m.r[16:24]==m.before_r[16:24] and m.r[29]==m.before_r[29] and m.r[30]==m.before_r[30] and m.f[20:]==m.before_f[20:]
def state(m):return m.memory,m.r,m.f,m.calls,m.observations,m.trace,m.hi,m.lo,m.current_pc,m.delay_of

def main():
    programs=[source.bound(*payload(source.OUT/name,source.NAME)) for name in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    n=0;seen=set()
    for c in cases():
        initial=fixture(c);machines=[]
        for words in programs:
            m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
        assert state(machines[0])==state(machines[2]);seen.update(machines[0].visits);n+=1
    private=0
    for alias,mode,phase,current in itertools.product(range(3),(0,3),(0,8),(0,255)):
        c=Case(alias=alias,mutation=mode,phase=phase,current=current,private_colors=True,seed=private)
        initial=fixture(c)
        for words in (programs[0],programs[2]):m=Oracle(words,initial,c);m.run();verify(m,initial,c)
        private+=1
    prefixes=0
    for c in (Case(),Case(alias=1,mutation=3),Case(present=0),Case(private_colors=True)):
        initial=fixture(c);m=Oracle(programs[0],initial,c);m.run()
        for cut in range(m.all_accesses):
            machines=[]
            for words in (programs[0],programs[2]):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing target memory boundary')
                machines.append(m)
            assert state(machines[0])==state(machines[1]);prefixes+=1
    missing=sorted(pc-source.ENTRY for pc in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen)
    report=dict(cases=n,streams=3,private_color_cases=private,full_state_prefixes=prefixes,visited_words=182-len(missing),unvisited_offsets=[hex(pc) for pc in missing],matrix_snapshots=True,raw_fault_order_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
