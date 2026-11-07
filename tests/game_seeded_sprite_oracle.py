"""Sentinel sprite descriptor, live O32 actor home and original timer callback."""
from dataclasses import dataclass
import itertools,struct
from tools.tests import game_selected_vertex_sprite_oracle as sprite
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ENTRY,ZERO,INITIALIZE,CREATE,RANDOM=0x15193390,0x100226F0,0x1516865C,0x15168800,0x150ADA20
ALLOCATE,COPY,CALLER,FREE,UPDATE=0x15167A68,0x10023A10,0x15149264,0x1516972C,0x150DBC60
ACTOR,OTHER,OUTPUT,HEADER=0x30000,0x31000,0x50000,0x70000
SENTINEL,TEXTURES,SEED,TICK,TABLE,UPDATES=0x800A81B0,0x8008CA4C,0x800885B0,0x800BE9E4,0x8008A4C0,0x8008A4E8
half=lambda n:((n&65535)^32768)-32768
u32=lambda n:n&0xFFFFFFFF
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
@dataclass(frozen=True)
class Case:
    x:int=17
    y:int=-32768
    z:int=-91
    height:int=-10000
    variant:int=0xDA
    random:int=0xFFFFFFFF
    phase:int=0
    mutation:int=0
    redirect:int=0
    connected:int=0
    outcome:int=1
    alias:int=0
    width:int=256
    tall:int=512
    seed:int=1
    sentinel:int=0xC61C4000
    timer:int=-1
    flags:int=0
    ticks:int=1
    update:int=0
    callback:int=1
def symbols():return dict(bzero=ZERO,func_1516865C=INITIALIZE,func_15168800=CREATE,func_150ADA20=RANDOM,D_800A81B0=SENTINEL,D_8008CA4C=TEXTURES)
def destination(c):return(OUTPUT,ACTOR-16,ACTOR,OTHER-16)[c.alias]
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+165)&255 for i in range(-1024,512)}
    for base,n in((ACTOR-32,576),(OTHER-32,576),(OUTPUT-32,320),(HEADER,32)):
        m.update({base+i:(i*29+90)&255 for i in range(n)})
    for p,values in((ACTOR,(c.x,c.y,c.z,c.height,c.variant)),(OTHER,(-32768,32767,41,123,0x33))):
        for i,v in enumerate(values[:4]):put(m,p+0x28+2*i,v,2)
        m[p+0x30]=values[4]&255;m[p+0xC]=0x83 if p==ACTOR else 0x45;m[p+1]=0xC1 if p==ACTOR else 0xEF;put(m,p+0xE,c.timer,2)
    m[ACTOR+0xD]=c.flags;m[ACTOR+0x10]=1 if c.callback else 255;m[ACTOR+0x11]=0 if c.update else 255
    put(m,s['D_800A81B0'],c.sentinel);put(m,s['D_8008CA4C']+69*4,HEADER);put(m,HEADER+6,c.width,2);put(m,HEADER+8,c.tall,2);put(m,SEED,c.seed,8);put(m,TICK,c.ticks);put(m,TABLE+4,ENTRY);put(m,UPDATES,UPDATE)
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}
def effect(m,c,s,stage,home):
    if stage==0 and c.mutation&1:
        for off,v in((0x28,32767),(0x2A,-32768),(0x2C,-32768),(0x2E,-10000)):put(m,ACTOR+off,v,2)
        m[ACTOR+0x30]=255
    if stage==1 and c.mutation&2:
        m[ACTOR+0xC]=33;m[ACTOR+1]=222;m[OTHER+0xC]=44;m[OTHER+1]=199
    if stage==2 and c.mutation&4:put(m,ACTOR+0xE,-123,2);m[ACTOR+0x30]=0xA7
    if stage==3 and c.mutation&8:put(m,ACTOR+0xE,-32768,2);m[ACTOR+0x30]=0x5A
    if c.redirect&(1<<stage)and stage in(0,1,3):put(m,home,OTHER)
def reference(initial,c=Case(),s=None,frame=216,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;m=dict(initial);packet=home-frame+40;calls=[];packets=[];put(m,home,ACTOR)
    calls.append((s['bzero'],(packet,168)))
    for i in range(168):m[packet+i]=0
    if not c.connected&1:effect(m,c,s,0,home)
    actor=read(m,home);p=actor+0x28;height=half(read(m,p+6,2))
    if floating(read(m,s['D_800A81B0']))==float(height):
        put(m,packet+0x96,half(read(m,p+2,2))-200,2);m[p+8]=0
    else:put(m,packet+0x96,height,2)
    for src,dst in((0,0x8C),(2,0x8E),(4,0x90)):put(m,packet+dst,read(m,p+src,2),2)
    for off,v,n in((0x92,0,2),(0x94,0,2),(0xA2,15,1),(0xA0,69,1),(0x86,10,2),(0xA3,m[p+8],1),(0x98,0x4880,2),(0xA4,128,1)):put(m,packet+off,v,n)
    calls.append((s['func_1516865C'],(packet,255,255,255,128)));sprite.initialize(m,packet,(255,255,255,128),s)
    if not c.connected&2:effect(m,c,s,1,home)
    actor=read(m,home);a=(packet,m[actor+0xC],m[actor+1]);calls.append((s['func_15168800'],a));packets.append(data(m,packet,168))
    if c.connected&4:calls.append((ALLOCATE,(14,a[2],184,1,a[1],1)))
    effect(m,c,s,2,home)
    if c.outcome:
        dest=destination(c)
        if c.connected&4:calls.append((COPY,(packet,dest+16,168)))
        for i,b in enumerate(packets[-1]):m[dest+16+i]=b
    calls.append((s['func_150ADA20'],()))
    if c.connected&8:value=next_seed(read(m,SEED,8));put(m,SEED,value,8);value=u32(value)
    else:effect(m,c,s,3,home);value=u32(c.random)
    put(m,read(m,home)+0xE,(value&127)+100,2)
    return dict(memory=public(m,c),calls=calls,packets=packets)
def caller_reference(initial,c,frame=216):
    m=dict(initial);calls=[];packets=[]
    if m[ACTOR+0xD]&1:put(m,ACTOR+0xE,half(read(m,ACTOR+0xE,2))-read(m,TICK),2)
    if m[ACTOR+0x11]!=255:calls.append((UPDATE,(ACTOR,)))
    if half(read(m,ACTOR+0xE,2))<0 and m[ACTOR+0x10]!=255:
        calls.append((ENTRY,(ACTOR,)));v=reference(m,c,frame=frame,home=STACK+c.phase-24);m=v['memory'];calls+=v['calls'];packets+=v['packets']
    if half(read(m,ACTOR+0xE,2))<0:calls.append((FREE,(ACTOR,)))
    return dict(memory=public(m,c),calls=calls,packets=packets)
class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None,frame=216,home=None):
        self.s=symbols()if s is None else s;self.frame=frame;self.home=STACK+c.phase if home is None else home;self.packets=[]
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(ACTOR,)if arguments is None else arguments)
    def execute(self,w):
        # The retained byte-copy loop uses trapping ADD for its end pointer.
        # Keep the trap distinction; do not silently interpret it as ADDU.
        if w>>26==0 and w&63==32:
            left,right=(signed32(self.r[w>>21&31]),signed32(self.r[w>>16&31]))
            value=left+right
            if not -(1<<31)<=value<(1<<31):raise ArithmeticError('MIPS ADD overflow')
            self.dispatched_word=w;self.r[w>>11&31]=u32(value);self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        counts={ENTRY:1,self.s['bzero']:2,self.s['func_1516865C']:5,self.s['func_15168800']:3,self.s['func_150ADA20']:0,ALLOCATE:6,COPY:3,UPDATE:1,FREE:1};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t==self.s['func_15168800']:self.packets.append(data(self.memory,a[0],168))
    def hook(self,t):
        c=self.case;s=self.s;a=self.calls[-1][1];value=0xA5000002
        if t==s['bzero']:
            assert a[1]==168
            for i in range(168):self.memory[a[0]+i]=0
            effect(self.memory,c,s,0,self.home)
        elif t==s['func_1516865C']:sprite.initialize(self.memory,a[0],a[1:],s);effect(self.memory,c,s,1,self.home)
        elif t in(s['func_15168800'],ALLOCATE):
            effect(self.memory,c,s,2,self.home);value=destination(c)if c.outcome else 0
            if value and t==s['func_15168800']:
                packet=data(self.memory,a[0],168)
                for i,b in enumerate(packet):self.memory[value+16+i]=b
        elif t==COPY:
            assert a[2]==168;packet=data(self.memory,a[0],168)
            for i,b in enumerate(packet):self.memory[a[1]+i]=b
        elif t==s['func_150ADA20']:effect(self.memory,c,s,3,self.home);value=u32(c.random)
        elif t in(UPDATE,FREE):pass
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helpers(rom,c,s=None):
    s=symbols()if s is None else s;code={}
    for bit,entry,offset,n in((1,s['bzero'],0x226F0,40),(2,s['func_1516865C'],0x195B0C,105),(4,s['func_15168800'],0x195CB0,28),(8,s['func_150ADA20'],0xDAED0,18)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    if c.connected&4:code.update(zip(range(COPY,COPY+784,4),struct.unpack_from('>196I',rom,0x23A10)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.packets,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for height,y,variant,random,mutation in itertools.product((-32768,-10001,-10000,-9999,0,32767),(-32768,-32569,-32568,-1,0,32767),(0,255),(0,127,0x80000000,0xFFFFFFFF),(0,15)):
        yield Case(height=height,y=y,variant=variant,random=random,mutation=mutation)
    for variant in range(256):yield Case(variant=variant,random=variant*1664525+1013904223)
    for alias,redirect,phase in itertools.product(range(4),(0,1,2,8,11),(0,8)):yield Case(alias=alias,redirect=redirect,phase=phase,mutation=15)
def canonical(calls,frame,home):return[(t,tuple('descriptor'if v==home-frame+40 else v for v in a))for t,a in calls]
def signed32(v):return((v&0xFFFFFFFF)^0x80000000)-0x80000000
