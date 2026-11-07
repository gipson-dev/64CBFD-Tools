"""Sprite callback, recaptured position, ordered draws and retained effect service."""
from dataclasses import dataclass,replace
import itertools,math,struct
from tools.tests import game_selected_vertex_sprite_oracle as sprite
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments import game_selected_impact_sprite_candidates as source
STACK,ACTOR,OWNER,OTHER,POSITIONS,OUTPUT,HEADER,SEED=sprite.STACK,sprite.ACTOR,sprite.OWNER,sprite.OTHER,sprite.POSITIONS,sprite.OUTPUT,sprite.HEADER,sprite.SEED
ENTRY,COLOR,CREATE,INTEGER,ALLOCATE,COPY=0x1518C69C,sprite.COLOR,sprite.CREATE,sprite.RANDOM,sprite.ALLOCATE,sprite.COPY
SELECTOR,FLOAT,SUBMIT,QUERY,EMIT_A,EMIT_B=0x151D8E20,0x150ADA68,0x151DBCBC,0x150A29C8,0x1513C73C,0x1513C5B0
STATE,GLOBAL_SELECTOR,COLORS,UNIT=0x800BE9F0,0x800E0A10,0x800AB414,0x8009F740
u32,half,byte,data=sprite.u32,sprite.half,sprite.byte,sprite.data
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
COLORS_DATA=bytes((i*13+90)&255 for i in range(768))
@dataclass(frozen=True)
class Case(sprite.Case):
    float_random:int=bits(.25)
    selector:int=129
    context:int=ACTOR+100
    mode:int=0
    alias:int=0
    state:int=1
    query:int=1
def symbols():
    s=sprite.symbols();s.update(func_151D8E20=SELECTOR,func_150ADA68=FLOAT,func_151DBCBC=SUBMIT);return s
def arguments(c):return(ACTOR,bits(3.25),bits(-4.5),bits(7.75),c.height,u32(c.context))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m=sprite.fixture(c,s)
    put(m,STATE,c.state);m[GLOBAL_SELECTOR]=c.selector&255;put(m,UNIT,0x37800000)
    for i,v in enumerate(COLORS_DATA):m[COLORS+i]=v
    return m
def public(m):return sprite.public(m)
def effect(m,c,stage,home):
    if stage in(0,1,2):sprite.effect(m,c,stage)
    if stage==2 and c.mode&1:
        put(m,ACTOR+0x94,POSITIONS+40);m[ACTOR+0x2D]=(m[ACTOR+0x2D]+1)&255
        i=byte(m[ACTOR+0x2D]);put(m,POSITIONS+i*20,bits(123.25));put(m,POSITIONS+i*20+8,bits(-77.5))
    if stage==3 and c.mode&2:
        m[ACTOR+0x2D]=(m[ACTOR+0x2D]+1)&255;put(m,ACTOR+0x94,POSITIONS+80);m[ACTOR+12]=33;m[ACTOR+1]=222
    if stage==4 and c.mode&4:m[ACTOR+12]=255;m[ACTOR+1]=129;put(m,ACTOR+0x98,OTHER)
    if stage==5 and c.mode&8:m[OWNER+32]=0xAA
    if stage==2 and c.alias&1:put(m,home+16,bits(-91.75))
    if stage==4 and c.alias&2:put(m,home+20,0xABCDEF01)
    if stage==3 and c.alias&4:
        for j,v in enumerate((bits(3.),bits(-4.),bits(5.))):put(m,home-192+4*j,v)
def packet_fields(packet):return bytes(v for i,v in enumerate(packet)if i not in(33,38,39))
def service_packet(m,selector):
    p=bytearray(40)
    def setv(off,v,n):p[off:off+n]=(v&((1<<(8*n))-1)).to_bytes(n,'big')
    for off,v,n in((0,0x67B02,4),(4,300,2),(6,56,1),(12,32768,4),(16,255,1),(17,255,1),(21,255,1),(23,6,1),(24,0x440001,4),(32,255,1),(34,1,2),(36,255,2)):setv(off,v,n)
    p[18:21]=data(m,COLORS+3*(selector&255),3)
    return packet_fields(p)
def reference(initial,c=Case(),s=None,frame=248):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase;descriptor=home-frame+80;position=home-frame+56;calls=[];packets=[];vectors=[];services=[];marks=[];integer_n=0
    put(m,home+16,c.height);put(m,home+20,c.context)
    owner=read(m,ACTOR+0x98);positions=read(m,ACTOR+0x94);i=byte(m[ACTOR+0x2D]);x=math.trunc(floating(read(m,positions+i*20)));z=math.trunc(floating(read(m,positions+i*20+8)));h=math.trunc(floating(c.height))
    for off,v,n in((0x80,0,4),(0x8A,256,2),(0x8C,x,2),(0x8E,h,2),(0x90,z,2)):put(m,descriptor+off,v,n)
    def integer():
        nonlocal integer_n
        calls.append((s['func_150ADA20'],()))
        if c.connected&4:v=sprite.next_seed(read(m,SEED,8));put(m,SEED,v,8)
        else:
            v=u32(c.random+17*integer_n)
            if integer_n==0:effect(m,c,0,home)
        integer_n+=1;return u32(v)
    lifetime=integer()%21+35
    for off,v,n in((0x92,lifetime,2),(0x94,lifetime,2),(0x96,h,2),(0x98,12,2),(0xA0,18,1),(0xA1,0,1),(0xA2,255,1)):put(m,descriptor+off,v,n)
    calls.append((s['func_1516865C'],(descriptor,255,255,255,255)));sprite.initialize(m,descriptor,(255,)*4,s)
    if not c.connected&1:effect(m,c,1,home)
    a=(descriptor,m[ACTOR+12],m[ACTOR+1]);calls.append((s['func_15168800'],a));packets.append(data(m,descriptor,168))
    if c.connected&2:calls.append((ALLOCATE,(14,a[2],184,1,a[1],1)))
    effect(m,c,2,home)
    if c.outcome:
        if c.connected&2:calls.append((COPY,(descriptor,OUTPUT+16,168)))
        for i,v in enumerate(packets[-1]):m[OUTPUT+16+i]=v
    m[owner+32]=4
    for j,v in enumerate((read(m,positions+byte(m[ACTOR+0x2D])*20),read(m,home+16),read(m,positions+byte(m[ACTOR+0x2D])*20+8))):put(m,position+4*j,v)
    calls.append((s['func_151D8E20'],()));marks.append(m[owner+32]);selected=c.selector&255
    if c.connected&16:
        if not read(m,STATE):
            calls.append((QUERY,(0,28)));effect(m,c,3,home)
            if not c.query:selected=10
    else:effect(m,c,3,home)
    calls.append((s['func_150ADA68'],()));marks.append(m[owner+32])
    if c.connected&8:v=sprite.next_seed(read(m,SEED,8));put(m,SEED,v,8);random=mul(bits(float(v&65535)),read(m,UNIT))
    else:effect(m,c,4,home);random=c.float_random
    scale=add(mul(random,bits(40.)),bits(100.));a=(selected,scale,255,read(m,home+20),position,m[ACTOR+12],m[ACTOR+1]);calls.append((s['func_151DBCBC'],a));marks.append(m[owner+32]);vectors.append(tuple(read(m,position+4*j)for j in range(3)))
    if c.connected&32:
        services.append(service_packet(m,selected));r=[integer()for _ in range(3)]if a[3]else[0,0,0];target=EMIT_A if a[3]else EMIT_B;local=home-frame-40;params=(local,0,0,a[3],*vectors[-1],scale,scale,r[0]&255,((r[2]&1)<<1)+(r[1]&1),0,a[5],a[6]);calls.append((target,params))
    effect(m,c,5,home)
    return dict(memory=m,calls=calls,packets=packets,vectors=vectors,services=services,marks=marks,value=1)
class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments_override=None,frame=248):
        self.s=symbols()if s is None else s;self.frame=frame;self.home=STACK+c.phase;self.packets=[];self.vectors=[];self.services=[];self.marks=[];self.integer_n=0
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=arguments(c)if arguments_override is None else arguments_override)
    def record_call(self,t):
        counts={ENTRY:6,self.s['func_150ADA20']:0,self.s['func_1516865C']:5,self.s['func_15168800']:3,self.s['func_151D8E20']:0,self.s['func_150ADA68']:0,self.s['func_151DBCBC']:7,QUERY:2,ALLOCATE:6,COPY:3,EMIT_A:14,EMIT_B:14};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t==self.s['func_15168800']:self.packets.append(data(self.memory,a[0],168))
        if t in(self.s['func_151D8E20'],self.s['func_150ADA68'],self.s['func_151DBCBC']):self.marks.append(self.memory[OWNER+32])
        if t==self.s['func_151DBCBC']:self.vectors.append(tuple(read(self.memory,a[4]+4*j)for j in range(3)))
        if t in(EMIT_A,EMIT_B):self.services.append(packet_fields(data(self.memory,a[0],40)))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xA5000002;fvalue=None
        if t==self.s['func_150ADA20']:
            value=u32(c.random+17*self.integer_n)
            if self.integer_n==0:effect(self.memory,c,0,self.home)
            self.integer_n+=1
        elif t==self.s['func_1516865C']:sprite.initialize(self.memory,a[0],a[1:],self.s);effect(self.memory,c,1,self.home)
        elif t==self.s['func_15168800']:
            effect(self.memory,c,2,self.home);value=OUTPUT if c.outcome else 0
            if value:
                for i,v in enumerate(data(self.memory,a[0],168)):self.memory[OUTPUT+16+i]=v
        elif t==ALLOCATE:effect(self.memory,c,2,self.home);value=OUTPUT if c.outcome else 0
        elif t==COPY:
            assert a[2]==168
            for i,v in enumerate(data(self.memory,a[0],a[2])):self.memory[a[1]+i]=v
        elif t==self.s['func_151D8E20']:effect(self.memory,c,3,self.home);value=c.selector&255
        elif t==QUERY:assert a==(0,28);effect(self.memory,c,3,self.home);value=c.query
        elif t==self.s['func_150ADA68']:effect(self.memory,c,4,self.home);fvalue=c.float_random
        elif t in(self.s['func_151DBCBC'],EMIT_A,EMIT_B):effect(self.memory,c,5,self.home)
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
        if fvalue is not None:self.f[0]=fvalue
def helper_code(rom,c,s=None):
    s=symbols()if s is None else s;code=sprite.helper_code(rom,c,s)
    for bit,entry,offset,n in((8,s['func_150ADA68'],0xDAF18,25),(16,s['func_151D8E20'],0x2062D0,19),(32,s['func_151DBCBC'],0x20916C,113)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.packets,m.vectors,m.services,m.marks)
def cases():
    for i in range(256):yield Case(index=i,random=u32(i*1664525+1013904223),height=bits((-1 if i&1 else 1)*(i*311+.75)),mutation=i%8,outcome=i&1,phase=8*(i&1),mode=i%16,selector=i)
    for rand,frac,mode,context in itertools.product((0,20,21,0x80000000,0xFFFFFFFF),(0,0x80000000,bits(.1),bits(1.),bits(-1.),bits(123.25)),(0,1,2,4,8,15),(0,ACTOR+100,0xABCDEF01)):yield Case(index=-3,random=rand,float_random=frac,mode=mode,context=context,mutation=7)
    for connected,seed,context,state,query in itertools.product((3,12,16,32,63),sprite.SEEDS,(0,ACTOR+100),(0,1),(0,1)):yield Case(connected=connected,seed=seed,context=context,state=state,query=query)
    for alias,phase,mode in itertools.product(range(1,8),(0,8),(0,15)):yield Case(alias=alias,phase=phase,mode=mode)
