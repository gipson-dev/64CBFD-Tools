"""Independent payload bytes, callback lifetimes and original helper windows."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,CREATE,COPY,ALLOCATE,ZERO=0x151D0F60,0x15149130,0x10022EC0,0x15167A68,0x100226F0
CALLBACKS=(0x151D1074,0x151D10A4,0x151D10C4)
COMMON,TRANSFORM,FAKE=0x151D10E4,0x15143134,0x17001000
TABLE,DEFAULT,ROWS,FLAG=0x8008FC30,0x800A5480,0x800AAF9C,0x800BE616
ACTOR,OUTPUT,MATRIX,MARK,LINK=0x30000,0x50000,0x90000,0x70000,0x72000
u32=lambda n:n&0xFFFFFFFF
VECTORS=((0x3F800000,0xC0200000,0x42C60000),(0xC7000000,0x3E800000,0x46FFFE00),(0x80000000,0,0xBF800000))
DEFAULTS=((0,0,0),(0x41200000,0xC1A00000,0x41F00000),(0x7FC12345,0x7F800000,0xFF800000))
@dataclass(frozen=True)
class Case:
    selector:int=0
    priority:int=255
    context:int=1
    identity:int=0x83
    result:int=1
    mask:int=7
    vector:int=0
    default:int=0
    mutation:int=0
    outcome:int=1
    alias:int=0
    phase:int=0
    connected:int=0
    matrix:int=1
    flag:int=0
    link:int=0
def symbols():return dict(D_8008FC30=TABLE,D_800A5480=DEFAULT,func_15149130=CREATE,memcpy=COPY)
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[p+i]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[p+i]=b
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def packet(home):return home-60
def destination(c,home):return(OUTPUT,ACTOR-40,DEFAULT-40,ACTOR,packet(home)-40,packet(home)-36)[c.alias]
def callback(c):return CALLBACKS[c.selector]if c.connected&1 else FAKE
def fixture(c=Case(),order='big'):
    m={STACK+c.phase+i:(i*17+165)&255 for i in range(-2048,512)}
    for p,n in((ACTOR-64,768),(OUTPUT-64,384),(DEFAULT-64,192),(TABLE,1024),(ROWS,24),(MATRIX,128),(MARK,16),(LINK,64)):
        for i in range(n):m[p+i]=(i*29+90)&255
    m[ACTOR+0x3B]=c.identity&255
    for off,v in zip((0x14,0x180,0x1C),VECTORS[c.vector]):wr(m,ACTOR+off,v,4,order)
    wr(m,ACTOR+0x1D4,MATRIX if c.matrix else 0,4,order);m[FLAG]=c.flag&255
    for i,v in enumerate(DEFAULTS[c.default]):wr(m,DEFAULT+i*4,v,4,order)
    for i in range(256):wr(m,TABLE+i*4,CALLBACKS[i]if c.connected&1 and i<3 else FAKE,4,order)
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-2048<=p<STACK+c.phase+512}
def callback_effect(m,c,home,order='big'):
    if c.mutation&1:m[ACTOR+0x3B]^=0x55
    if c.mutation&2:
        for i,v in enumerate(VECTORS[1]):wr(m,DEFAULT+i*4,v,4,order)
    if c.mutation&4:
        wr(m,home+4,0xABCDE000|((c.selector^0x80)&255),4,order)
        wr(m,home+8,0x12340000|((c.priority^0x5A)&255),4,order);wr(m,home+12,0x80000001,4,order)
def factory_effect(m,c,home,order='big'):
    if c.mutation&8:
        m[ACTOR+0x3B]^=0xAA
        for i,v in enumerate(VECTORS[2]):wr(m,DEFAULT+i*4,v,4,order)
    if c.mutation&16:wr(m,packet(home)+8,0xDEADBEEF,4,order);m[packet(home)+0x34]^=0x33
def initialize(m,p,args,order='big'):
    wr(m,p+0xE,args[0],2,order)
    for off,v in((0x10,args[1]),(0x11,args[2]),(0x12,args[3]),(0xD,args[4]),(0x13,args[5])):m[p+off]=v&255
    for i in range(16):m[p+20+i]=0
def reference(initial,c=Case(),home=None,order='big'):
    home=STACK+c.phase if home is None else home;m=dict(initial);p=packet(home);calls=[];packets=[]
    for off,v in((4,c.selector),(8,c.priority),(12,c.context)):wr(m,home+off,v,4,order)
    wr(m,p,ACTOR,4,order);m[p+4]=m[ACTOR+0x3B];wr(m,p+8,0,4,order)
    def call(t,args):calls.append((t,tuple(map(u32,args))))
    call(callback(c),(ACTOR,p+24))
    if c.connected&1:
        if c.selector==0:
            for off,v in enumerate((rd(m,ACTOR+0x14,4,order),bits(floating(rd(m,ACTOR+0x180,4,order))+8.0),rd(m,ACTOR+0x1C,4,order))):wr(m,p+24+4*off,v,4,order)
            result=1
        else:
            call(COMMON,(ACTOR,p+24,c.selector-1));result=1 if rd(m,ACTOR+0x1D4,4,order)else 0
            if result:
                call(TRANSFORM,(ROWS+(c.selector-1)*12,p+24,rd(m,ACTOR+0x1D4,4,order)))
                for i,v in enumerate(VECTORS[c.vector]):wr(m,p+24+i*4,v,4,order)
    else:
        for i,v in enumerate(VECTORS[c.vector]):
            if c.mask&(1<<i):wr(m,p+24+i*4,v,4,order)
        callback_effect(m,c,home,order);result=c.result
    if not result:
        for i in range(3):wr(m,p+24+i*4,rd(m,DEFAULT+i*4,4,order),4,order)
    for i in range(3):wr(m,p+12+i*4,rd(m,p+24+i*4,4,order),4,order)
    for i in range(3):wr(m,p+36+i*4,rd(m,DEFAULT+i*4,4,order),4,order)
    wr(m,p+48,0,4,order);m[p+52]=rd(m,home+4,4,order)&255
    args=(300,0xFFFFFFFF,95,0xFFFFFFFF,0,72,56,rd(m,home+8,4,order)&255,rd(m,home+12,4,order));call(CREATE,args);packets.append((CREATE,data(m,p,56)))
    dest=destination(c,home)
    if c.connected&2:call(ALLOCATE,(35,args[8],96,1,args[7],1))
    factory_effect(m,c,home,order)
    if c.outcome:
        if c.alias<4:initialize(m,dest,args,order)
        if c.connected&2:call(ZERO,(dest+20,16))
        call(COPY,(dest+40,p,56));packets.append((COPY,data(m,p,56)))
        for i in range(56):m[dest+40+i]=m[p+i]
    return dict(memory=public(m,c),full_memory=m,calls=calls,packets=packets)
def caller_reference(initial,c,caller):
    if caller==0x1514DC5C:
        v=reference(initial,replace(c,selector=0,priority=255,context=1),home=STACK+c.phase-24);v['calls'].insert(0,(ENTRY,(ACTOR,0,255,1)));return v
    home=STACK+c.phase-80;m=dict(initial);calls=[];packets=[]
    for selector in(1,2):
        case=replace(c,selector=selector,priority=255,context=1);v=reference(m,case,home=home);m=v['full_memory'];calls.append((ENTRY,(ACTOR,selector,255,1)));calls.extend(v['calls']);packets.extend(v['packets'])
    calls.append((0x151BB044,(ACTOR,)))
    if not m[FLAG]:calls.append((0x151BC074,(ACTOR,)))
    calls.extend(((0x151BD2F8,(ACTOR,255,1)),(0x151B9F00,(ACTOR,255,1))))
    for vector,kind,values in((0x800A5958,12,(300,12,255,255,255,2,0,0xFFFFFFFF,0,0,255,1)),(0x800A5964,15,(300,15,255,0,0,255,1,0xFFFFFFFF,0,0,255,1))):
        calls.append((0x15160A58,(ACTOR,1,vector,2,*values)))
    if c.link:calls.append((0x1514EC1C,(LINK,ACTOR,25)))
    return dict(memory=public(m,c),full_memory=m,calls=calls,packets=packets)
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):
        self.home=STACK+c.phase;self.packets=[]
        super().__init__(words,memory,c,entry=entry,s=symbols(),connected=connected,arguments=(ACTOR,c.selector,c.priority,u32(c.context)))
    def record_call(self,t):
        counts={ENTRY:4,FAKE:2,**{cb:2 for cb in CALLBACKS},COMMON:3,TRANSFORM:3,CREATE:9,COPY:3,ALLOCATE:6,ZERO:2,0x151BB044:1,0x151BC074:1,0x151BD2F8:3,0x151B9F00:3,0x15160A58:16,0x1514EC1C:3};assert t in counts,hex(t)
        args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==ENTRY:self.home=self.r[29]
        if t==CREATE:self.packets.append((t,data(self.memory,packet(self.home),56)))
        if t==COPY:self.packets.append((t,data(self.memory,args[1],args[2])))
    def hook(self,t):
        c=self.case;args=self.calls[-1][1];value=0xA5000002
        if t==FAKE:
            for i,v in enumerate(VECTORS[c.vector]):
                if c.mask&(1<<i):wr(self.memory,args[1]+4*i,v)
            callback_effect(self.memory,replace(c,selector=rd(self.memory,self.home+4)&255,priority=rd(self.memory,self.home+8)&255),self.home);value=u32(c.result)
        elif t==TRANSFORM:
            for i,v in enumerate(VECTORS[c.vector]):wr(self.memory,args[1]+4*i,v)
        elif t in(CREATE,ALLOCATE):
            factory_effect(self.memory,c,self.home);value=destination(c,self.home)if c.outcome else 0
            if value and t==CREATE and c.alias<4:initialize(self.memory,value,args)
        elif t==ZERO:
            assert args[1]==16
            for i in range(16):self.memory[args[0]+i]=0
        elif t==COPY:
            assert args[2]==56
            for i in range(args[2]):self.memory[args[0]+i]=self.memory[args[1]+i]
            value=args[0]
        elif t==0x15160A58:value=LINK if c.link else 0
        elif t in(0x151BB044,0x151BC074,0x151BD2F8,0x151B9F00,0x1514EC1C):pass
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helpers(rom,c):
    code={}
    descriptors=[]
    if c.connected&1:descriptors.extend(((CALLBACKS[0],0x1FE524,12),(CALLBACKS[1],0x1FE554,8),(CALLBACKS[2],0x1FE574,8),(COMMON,0x1FE594,21)))
    if c.connected&2:descriptors.extend(((CREATE,0x1765E0,49),(ZERO,0x226F0,40)))
    if c.connected&4:descriptors.append((COPY,0x22EC0,11))
    for e,p,n in descriptors:code.update(zip(range(e,e+n*4,4),struct.unpack_from('>%dI'%n,rom,p)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.packets,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for selector in range(256):yield Case(selector=selector,priority=selector,identity=selector)
    for result,mask,mutation,outcome in itertools.product((0,1,0xFFFFFFFF,0x80000000),range(8),(0,1,2,4,8,16,31),(0,1)):
        yield Case(result=result,mask=mask,mutation=mutation,outcome=outcome,priority=0x80,context=0x80000000)
    for alias,result,phase in itertools.product(range(1,6),(0,1),(0,8)):yield Case(alias=alias,result=result,phase=phase,mutation=3)
    for vector,default in itertools.product(range(3),range(3)):yield Case(vector=vector,default=default)
