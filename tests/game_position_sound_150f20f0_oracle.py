"""Quartic-position sound, wrapping cooldown and retained spatial outputs."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.tests.test_game_view_fov_transfer import fp
ENTRY,RECORDS,COOLDOWN,TICKS,THRESHOLD=0x150F20F0,0x800CC2D0,0x800D98F0,0x800BE9E4,0x800A191C
SPATIAL,RANDOM,AUDIO,INNER,PLAY=0x100114D0,0x150ADA20,0x10010F30,0x1000A420,0x10010BE8
LISTENERS,COUNT,VOICE=0x80041F68,0x80082FA0,0x80041FD9
SYMS=dict(D_800CC2D0=RECORDS,D_800D98F0=COOLDOWN,D_800BE9E4=TICKS,D_800A191C=THRESHOLD,func_100114D0=SPATIAL,func_150ADA20=RANDOM,func_10010F30=AUDIO)
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    index:int=0
    x:int=0x42C80000
    y:int=0xC1080000
    z:int=0
    cooldown:int=0
    ticks:int=1
    randoms:tuple=(0xFFFFFFFF,0x80000000)
    outputs:tuple=(0x7FFFFFFF,0x87654321,0xFEDCBA98)
    overrides:tuple=(0xFFFFFFF0,0x87654321)
    mutation:int=0
    phase:int=0
    listeners:int=0
    attenuation:int=0x87654321

def data(m,p,n):return bytes(m[u32(p+j)]for j in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def record(c,s=SYMS):return u32(s['D_800CC2D0']+u32(c.index*812))
def magnitude(x,z):
    a,b=fp(x,x,'mul'),fp(z,z,'mul');return fp(fp(a,a,'mul'),fp(b,b,'mul'),'add')
def fixture(c,s=SYMS):
    m={STACK+j:(j*17+165)&255 for j in range(-2048,2048)}
    base=s['D_800CC2D0']
    for index in range(26):
        a=u32(base+index*812)
        for j in range(812):m[u32(a+j)]=(j*29+index*13+90)&255
        for off in(20,24,28):put(m,u32(a+off),0)
    a=record(c,s)
    if not all(u32(a+j)in m for j in range(812)):
        m.update({u32(a+j):(j*29+90)&255 for j in range(812)})
    for off,w in zip((20,24,28),(c.x,c.y,c.z)):put(m,u32(a+off),w)
    put(m,s['D_800BE9E4'],u32(c.ticks));put(m,s['D_800D98F0'],c.cooldown,1);put(m,s['D_800A191C'],0x4ACE4C80)
    for index in range(4):
        for j,w in enumerate((index*3,index*4,index*5,index*7-4,index*11-9,index*13-7,0x3F000000+index*0x80000)):put(m,LISTENERS+index*28+j*4,u32(w))
    put(m,COUNT,c.listeners);m[VOICE]=0xA6
    return m

def effect(m,c,stage,home,s=SYMS,outputs=None):
    out0=home-12 if outputs is None else outputs[0]
    if stage==0:
        if c.mutation&1:put(m,s['D_800D98F0'],0x31,1)
        if c.mutation&32:
            put(m,s['D_800BE9E4'],0x80000000)
            for off,w in zip((20,24,28),(0xC2C80000,0x41A00000,0x42480000)):put(m,u32(record(c,s)+off),w)
    elif stage==1:
        if c.mutation&2:put(m,out0,c.overrides[0])
        if c.mutation&64:put(m,s['D_800D98F0'],0x55,1)
    elif stage==2:
        if c.mutation&4:put(m,out0,c.overrides[1])
        if c.mutation&8:put(m,s['D_800D98F0'],0x23,1)
    elif stage==3:
        if c.mutation&16:put(m,s['D_800D98F0'],0x6A,1)

def snapshot(m,c,stage,args,home,s=SYMS,output_pointers=None):
    position=tuple(read(m,u32(record(c,s)+o))for o in(20,24,28));outputs=None if stage==0 else tuple(read(m,p)for p in ((home-12,home-16,home-20)if output_pointers is None else output_pointers))
    return(stage,args,read(m,s['D_800D98F0'],1),read(m,s['D_800BE9E4']),position,outputs)

def reference(initial,c,home=None,s=SYMS):
    home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];snapshots=[];a=record(c,s)
    mag=magnitude(read(m,u32(a+20)),read(m,u32(a+28)));cooldown=read(m,s['D_800D98F0'],1)
    if cooldown:
        tick=read(m,s['D_800BE9E4']);put(m,s['D_800D98F0'],u32(cooldown-tick)&255 if signed(tick)<cooldown else 0,1)
        return m,calls,snapshots,mag
    if not floating(read(m,s['D_800A191C']))<floating(mag):return m,calls,snapshots,mag
    def call(stage,name,args):calls.append((s[name],args));snapshots.append(snapshot(m,c,stage,args,home,s))
    call(0,'func_100114D0',(0,trunc(read(m,u32(a+24))),0,32767,20000,19000,home-12,home-16,home-20))
    for j,w in enumerate(c.outputs):put(m,home-12-j*4,w)
    effect(m,c,0,home,s);put(m,home-12,u32(read(m,home-12)+128))
    call(1,'func_150ADA20',());effect(m,c,1,home,s);put(m,s['D_800D98F0'],(c.randoms[0]&127)+128,1)
    call(2,'func_150ADA20',());effect(m,c,2,home,s)
    call(3,'func_10010F30',(108+u32(c.randoms[1])%3,24000,read(m,home-9,1),0,0));effect(m,c,3,home,s)
    return m,calls,snapshots,mag

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,arguments=None):
        self.snapshots=[];self.draw=0;self.semantic_home=STACK+c.phase;self.outputs=None
        super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(u32(c.index),)if arguments is None else arguments)
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==13:
            prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
            try:self.f[w>>6&31]=trunc(self.f[w>>11&31])
            finally:self.own_instruction=prior
        else:super().execute(w)
    def record_call(self,t):
        s=self.syms
        if t==s['func_100114D0']:stage=0;args=tuple(map(u32,self.arguments(9)));self.outputs=args[6:]
        elif t==s['func_150ADA20']:stage=1+self.draw;args=();self.draw+=1
        else:assert t==s['func_10010F30'],hex(t);stage=3;args=tuple(map(u32,self.arguments(5)))
        self.calls.append((t,args));self.snapshots.append(snapshot(self.memory,self.case,stage,args,self.semantic_home,s,self.outputs));self.events.append(('CALL',t,args))
    def hook(self,t):
        s=self.syms;c=self.case;stage=0 if t==s['func_100114D0']else self.draw if t==s['func_150ADA20']else 3
        if stage==0:
            for p,w in zip(self.outputs,c.outputs):put(self.memory,p,w)
        effect(self.memory,c,stage,self.semantic_home,s,self.outputs)
        for j in range(4):self.put(u32(self.r[29]+j*4),0xB5000000+j,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=u32(c.randoms[stage-1])if stage in(1,2)else 0x87654321

def edge_pairs():
    center=bits((6760000-50**4)**0.25);hits=[]
    for z in range(center-32,center+33):
        if magnitude(bits(50.),z)==0x4ACE4C80:hits.append((bits(50.),z))
    assert hits,'Missing actual-threshold equality control';return(hits[0][0],hits[0][1]-1),hits[0],(hits[-1][0],hits[-1][1]+1)

def cases():
    for cooldown,tick in itertools.product(range(256),(0,1,0x80000000,0xFFFFFFFF)):
        yield Case(index=cooldown%26,cooldown=cooldown,ticks=tick,phase=(cooldown&1)*8)
    for mu,phase in itertools.product(range(128),(0,8)):
        yield Case(index=mu%26,mutation=mu,phase=phase,outputs=((0,0x7FFFFFFF,0xFFFFFFFF,0xFFFFFF80)[mu%4],0x87654321,0xFEDCBA98),randoms=((0,1,127,128,0xFFFFFFFF)[mu%5],(0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[mu%6]))
    profiles=[(bits(0.),bits(0.)),(0x80000000,bits(0.)),(1,0x80000001),(bits(50.),0),(bits(51.),0),(bits(-100.),bits(25.)),(bits(1e10),0),(0x7F800000,0),(0x7FC01234,0),*edge_pairs()]
    for j,(x,z)in enumerate(profiles):
        for cooldown,phase in itertools.product((0,1),(0,8)):
            yield Case(index=j%26,x=x,z=z,cooldown=cooldown,phase=phase,y=0x7FC01234 if j==5 else Case.y)
    inverse=pow(203,-1,1<<30);alias=(((COOLDOWN-20-RECORDS)&0xFFFFFFFF)//4*inverse)%(1<<30)
    for index,phase,cooldown in itertools.product((0xFFFFFFFF,26,0x80000000,0x7FFFFFFF,alias),(0,8),(0,1)):
        yield Case(index=index,phase=phase,cooldown=cooldown)
