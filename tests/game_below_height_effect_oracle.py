"""Retained pointers, double threshold and live post-provider field accesses."""
from dataclasses import dataclass
import itertools,math,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_selected_impact_sprite_oracle import service_packet
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ENTRY,FLOAT,SELECTOR,SUBMIT,QUERY,EMIT=0x15189EBC,0x150ADA68,0x151D8E20,0x151DBCBC,0x150A29C8,0x1513C5B0
ACTOR,POSITIONS,PAYLOAD,OTHER=0x30000,0x50000,0x60000,0x61000
THRESHOLD,RESET,SEED,UNIT,STATE,GLOBAL_SELECTOR,COLORS=0x800A73A8,0x800A73B0,0x800885B0,0x8009F740,0x800BE9F0,0x800E0A10,0x800AB414
u32=lambda n:n&0xFFFFFFFF
byte=lambda n:((n&255)^128)-128
dbits=lambda x:struct.unpack('>Q',struct.pack('>d',x))[0]
double=lambda n:struct.unpack('>d',struct.pack('>Q',n))[0]
mul=lambda a,b:bits(floating(a)*floating(b))
@dataclass(frozen=True)
class Case:
    index:int=0
    height:int=0x418E0000
    y:int=0x3F800000
    random:int=0x3E800000
    selector:int=129
    mutation:int=0
    alias:int=0
    phase:int=0
    connected:int=0
    seed:int=1
    state:int=1
    query:int=1
    threshold:int=0x3FE999999999999A
def symbols():return dict(func_150ADA68=FLOAT,func_151D8E20=SELECTOR,func_151DBCBC=SUBMIT,D_800A73A8=THRESHOLD,D_800A73B0=RESET)
def payload(c):return (PAYLOAD,ACTOR+0x80,POSITIONS+byte(c.index)*20-0x48,ACTOR)[c.alias]
def fixture(rom,c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+165)&255 for i in range(-1024,256)}
    for base,n in((ACTOR,512),(POSITIONS-2700,5500),(PAYLOAD,256),(OTHER,256)):
        m.update({base+i:(i*29+90)&255 for i in range(n)})
    for i in range(-128,128):
        for off,value in((0,bits(i+3.25)),(4,c.y),(8,bits(-i-4.5))):put(m,POSITIONS+i*20+off,value)
    p=payload(c);put(m,p,bits(2.5));put(m,p+0x48,c.height);m[p+0x1B]=0xDA;m[p+0x20]=0
    m[ACTOR+0x2D]=c.index&255;m[ACTOR+0xC]=0x83;m[ACTOR+1]=0xC1;put(m,ACTOR+0x94,POSITIONS);put(m,ACTOR+0x98,p)
    put(m,s['D_800A73A8'],c.threshold,8);put(m,s['D_800A73B0'],0xC61C4000)
    put(m,SEED,c.seed,8);put(m,UNIT,0x37800080);put(m,STATE,c.state);m[GLOBAL_SELECTOR]=c.selector&255
    for i,v in enumerate(rom[0x24FED4:0x24FED4+768]):m[COLORS+i]=v
    return m
def public(m,c):return {p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+256}
def effect(m,c,s,stage,p):
    if stage==0 and c.mutation&1:
        m[ACTOR+0x2D]=(m[ACTOR+0x2D]+1)&255;put(m,ACTOR+0x94,POSITIONS+80);put(m,ACTOR+0x98,OTHER);put(m,p+0x48,bits(41.25))
        put(m,s['D_800A73A8'],dbits(.5),8)
    if stage==1 and c.mutation&2:
        m[ACTOR+0x2D]=(m[ACTOR+0x2D]+1)&255;put(m,ACTOR+0x94,POSITIONS+160);put(m,ACTOR+0x98,OTHER)
        put(m,p,bits(-3.25));m[p+0x1B]=0xF1;m[ACTOR+0xC]=33;m[ACTOR+1]=222;put(m,p+0x48,bits(-91.5))
    if stage==2 and c.mutation&4:
        put(m,ACTOR+0x98,OTHER);m[p+0x20]=0xAA;put(m,s['D_800A73B0'],bits(99.75))
def reference(initial,c=Case(),s=None,frame=80):
    s=symbols()if s is None else s;m=dict(initial);p=read(m,ACTOR+0x98);positions=read(m,ACTOR+0x94);home=STACK+c.phase;point=home-frame+0x34;calls=[];vectors=[];services=[]
    if floating(read(m,positions+byte(m[ACTOR+0x2D])*20+4))<floating(read(m,p+0x48)):
        calls.append((s['func_150ADA68'],()))
        if c.connected&1:
            value=next_seed(read(m,SEED,8));put(m,SEED,value,8);random=mul(bits(float(value&65535)),read(m,UNIT))
        else:effect(m,c,s,0,p);random=c.random
        if floating(random)<double(read(m,s['D_800A73A8'],8)):
            vector=(read(m,positions+byte(m[ACTOR+0x2D])*20),read(m,p+0x48),read(m,positions+byte(m[ACTOR+0x2D])*20+8))
            for i,v in enumerate(vector):put(m,point+4*i,v)
            calls.append((s['func_151D8E20'],()));selector=c.selector&255
            if c.connected&2:
                if not read(m,STATE):
                    calls.append((QUERY,(0,28)));effect(m,c,s,1,p)
                    if not c.query:selector=10
            else:effect(m,c,s,1,p)
            scale=mul(read(m,p),bits(6.));a=(selector,scale,m[p+0x1B],0,point,m[ACTOR+0xC],m[ACTOR+1]);calls.append((s['func_151DBCBC'],a));vectors.append(vector)
            if c.connected&4:
                packet=bytearray(service_packet(m,selector));packet[16]=a[2]&255
                services.append(bytes(packet));local=home-frame-40
                calls.append((EMIT,(local,0,0,0,*vector,scale,scale,0,0,0,a[5],a[6])))
            effect(m,c,s,2,p)
        m[p+0x20]=4;put(m,p+0x48,read(m,s['D_800A73B0']))
    return dict(memory=public(m,c),calls=calls,vectors=vectors,services=services,value=1)
class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None,frame=80):
        self.s=symbols()if s is None else s;self.frame=frame;self.p=read(memory,ACTOR+0x98);self.home=STACK+c.phase;self.vectors=[];self.services=[]
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(ACTOR,)if arguments is None else arguments)
    def execute(self,w):
        op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and(fmt,fn)in((16,33),(17,60)):
            self.dispatched_word=w
            if fmt==16:
                value=dbits(floating(self.f[fs]));self.f[fd],self.f[fd+1]=value&0xFFFFFFFF,value>>32
            else:self.condition=double(self.f[fs]|self.f[fs+1]<<32)<double(self.f[ft]|self.f[ft+1]<<32)
            self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        counts={ENTRY:1,self.s['func_150ADA68']:0,self.s['func_151D8E20']:0,self.s['func_151DBCBC']:7,QUERY:2,EMIT:14};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==self.s['func_151DBCBC']:self.vectors.append(tuple(read(self.memory,a[4]+4*i)for i in range(3)))
        if t==EMIT:
            from tools.tests.game_selected_impact_sprite_oracle import packet_fields
            self.services.append(packet_fields(bytes(self.memory[a[0]+i]for i in range(40))))
    def hook(self,t):
        c=self.case;s=self.s;value=0xA5000002;fvalue=None
        if t==s['func_150ADA68']:effect(self.memory,c,s,0,self.p);fvalue=c.random
        elif t==s['func_151D8E20']:effect(self.memory,c,s,1,self.p);value=c.selector&255
        elif t==QUERY:effect(self.memory,c,s,1,self.p);value=c.query
        elif t in(s['func_151DBCBC'],EMIT):effect(self.memory,c,s,2,self.p)
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
        if fvalue is not None:self.f[0]=fvalue
def helper_code(rom,c,s=None):
    s=symbols()if s is None else s;code={}
    for bit,entry,offset,n in((1,s['func_150ADA68'],0xDAF18,25),(2,s['func_151D8E20'],0x2062D0,19),(4,s['func_151DBCBC'],0x20916C,113)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.events,m.calls,m.vectors,m.services,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def canonical(calls,frame,phase):
    point=STACK+phase-frame+0x34;packet=STACK+phase-frame-40
    return [(t,tuple('vector'if v==point else'descriptor'if v==packet else v for v in a))for t,a in calls]
def cases():
    for i in range(256):yield Case(index=i,selector=i,mutation=i%8,phase=8*(i&1))
    values=(0,0x80000000,bits(-1.),bits(1.),bits(17.75),0x7F800000,0xFF800000,0x7FC12345)
    for height,y,random,mutation in itertools.product(values,values,(bits(.25),bits(.79999995),bits(.8),bits(1.),0x7FC12345),(0,7)):
        yield Case(height=height,y=y,random=random,mutation=mutation)
    for alias,index,mutation in itertools.product(range(4),(-128,-3,0,127),range(8)):
        yield Case(alias=alias,index=index,mutation=mutation)
