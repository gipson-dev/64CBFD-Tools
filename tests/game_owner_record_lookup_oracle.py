"""Two ordered owner/tag chains, canonical switch data and original constructor."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ENTRY,CREATE,ALLOCATE,COPY,RANDOM=0x1518BA90,0x1518BCD0,0x15167A68,0x10022EC0,0x150ADA20
TABLE,END,JUMP=0x800DCE50,0x800DD190,0x800A7410
CONSTANTS=(0x800A7434,0x800A7438,0x800A743C)
OWNER,OTHER,NODES,OUTPUT,ALTERNATE,SEED=0x220000,0x221000,0x230000,0x240000,0x250000,0x800885B0
JUMPS=(164,256,256,256,256,256,312,312,172)
u32=lambda n:n&0xFFFFFFFF
data=lambda m,p,n:bytes(m[u32(p+i)]for i in range(n))
@dataclass(frozen=True)
class Case:
    null:int=0
    kind:int=0
    tag:int=37
    priority:int=255
    context:int=0
    heads:tuple=(0,3)
    pointers:int=0
    tags:int=0
    owner_node:int=-1
    outcome:int=1
    mutation:int=0
    alias:int=0
    phase:int=0
    seed:int=1
    connected:int=0
    randoms:tuple=(0xFFFFFFFF,0x80000000)
    constants:tuple=(0x4030A3D7,0x40BEB852,0x404D70A4)
def owner(c):return 0 if c.null else NODES+128*c.owner_node if c.owner_node>=0 else OWNER
def symbols():return dict(D_800DCE50=TABLE,D_800DD190=END,jtbl_800A7410=JUMP,**{'.rodata':JUMP},D_800A7434=CONSTANTS[0],D_800A7438=CONSTANTS[1],D_800A743C=CONSTANTS[2],func_1518BCD0=CREATE)
def arguments(c):return(owner(c),u32(c.priority),u32(c.context))
def fixture(c=Case(),s=None,entry=ENTRY):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-512,256)}
    for p,n in((OWNER,80),(OTHER,80),(NODES,6*128),(OUTPUT-16,100),(ALTERNATE,32),(s['D_800DCE50'],832)):
        m.update({p+i:(i*7+c.seed*11+90)&255 for i in range(n)})
    for i in range(6):
        p=NODES+128*i;put(m,p+8,0 if i in(2,5)else p+128);put(m,p+0x24,owner(c)if c.pointers>>i&1 else OTHER);m[p+0x28]=c.tag&255 if c.tags>>i&1 else(c.tag+1+i)&255
    if owner(c):m[owner(c)+4]=c.kind&255;m[owner(c)+59]=c.tag&255
    for row,head in enumerate(c.heads):put(m,s['D_800DCE50']+0x7C+row*416,0 if head<0 else NODES+128*head)
    for i,off in enumerate(JUMPS):put(m,s['jtbl_800A7410']+4*i,entry+off)
    for name,value in zip(('D_800A7434','D_800A7438','D_800A743C'),c.constants):put(m,s[name],value)
    put(m,SEED,c.seed,8);return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-512<=p<STACK+c.phase+256}
def effect(m,c,stage,home):
    if c.mutation&1 and owner(c):m[owner(c)+59]^=0x55
    if c.mutation&2:put(m,TABLE+0x7C,0);put(m,CONSTANTS[0],0x7FC12345)
    if c.alias&1 and stage==ALLOCATE:put(m,home-72,ALTERNATE)
    if c.alias&2 and stage==ALLOCATE:put(m,home-64,0xABCDEF01)
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];packets=[];traversed=[];home=STACK+c.phase;a=owner(c)
    if not a:return dict(memory=m,calls=calls,packets=packets,value=0,traversed=traversed)
    row=s['D_800DCE50']
    while True:
        p=read(m,row+0x7C)
        while p:
            traversed.append(p)
            if read(m,p+0x24)==a or m[a+59]==m[p+0x28]:return dict(memory=m,calls=calls,packets=packets,value=p,traversed=traversed)
            p=read(m,p+8)
        row+=416
        if row==s['D_800DD190']:break
    kind=m[a+4]
    if kind not in(0,1,2,3,4,7):return dict(memory=m,calls=calls,packets=packets,value=0,traversed=traversed)
    p=home-32;values=(read(m,s['D_800A7434']),read(m,s['D_800A7438']),read(m,s['D_800A743C']),bits(5.))if kind==7 else(bits(10.),)*4
    for i,v in enumerate(values):put(m,p+4*i,v)
    put(m,p+16,4 if kind==7 else 5,2);put(m,p+18,55 if kind==7 else 0,2);put(m,p+20,a);m[p+24]=m[a+59];m[p+25]=5;m[p+26]=19
    packet=data(m,p,28);packets.append(packet);calls.append((s['func_1518BCD0'],(p,c.priority&255,u32(c.context))))
    if not c.connected&1:
        effect(m,c,s['func_1518BCD0'],home)
        if c.outcome:m[OUTPUT]^=0xA5
        return dict(memory=m,calls=calls,packets=packets,value=OUTPUT if c.outcome else 0,traversed=traversed)
    calls.append((ALLOCATE,(31,u32(c.context),68,1,c.priority&255,1)));effect(m,c,ALLOCATE,home)
    if not c.outcome:return dict(memory=m,calls=calls,packets=packets,value=0,traversed=traversed)
    source=ALTERNATE if c.alias&1 else p;calls.append((COPY,(OUTPUT+16,source,28)))
    for i,v in enumerate(data(m,source,28)):m[OUTPUT+16+i]=v
    for i,off in enumerate((44,48)):
        calls.append((RANDOM,()))
        if c.connected&4:r=next_seed(read(m,SEED,8));put(m,SEED,r,8)
        else:r=c.randoms[i]
        put(m,OUTPUT+off,r&31)
    return dict(memory=m,calls=calls,packets=packets,value=OUTPUT,traversed=traversed)
class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments_override=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.packets=[];self.draws=0
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=arguments(c)if arguments_override is None else arguments_override)
    def record_call(self,t):
        counts={ENTRY:3,self.s['func_1518BCD0']:3,ALLOCATE:6,COPY:3,RANDOM:0};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t==self.s['func_1518BCD0']:self.packets.append(data(self.memory,a[0],28))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xA5000002
        if t==self.s['func_1518BCD0']:
            effect(self.memory,c,t,self.home);value=OUTPUT if c.outcome else 0
            if value:self.memory[OUTPUT]^=0xA5
        elif t==ALLOCATE:effect(self.memory,c,t,self.home);value=OUTPUT if c.outcome else 0
        elif t==COPY:
            assert a[2]==28
            for i,v in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=v
            value=a[0]
        elif t==RANDOM:value=c.randoms[self.draws];self.draws+=1
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helper_code(rom,c,s=None):
    s=symbols()if s is None else s;code={}
    for bit,entry,offset,n in((1,s['func_1518BCD0'],0x1B9180,36),(2,COPY,0x22EC0,11),(4,RANDOM,0xDAED0,18)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.packets,m.draws)
def cases():
    for kind,layout in itertools.product(range(256),range(4)):
        yield Case(kind=kind,heads=((0,3),(-1,3),(0,-1),(-1,-1))[layout],priority=u32(kind*1664525+1013904223),context=u32(kind*0x1020304),tag=kind,outcome=kind&1,phase=8*(kind&1))
    for slot,match,kind,heads in itertools.product(range(6),range(3),(0,7,255),((0,3),(-1,3),(0,-1))):yield Case(pointers=(1<<slot)if match!=1 else 0,tags=(1<<slot)if match else 0,kind=kind,heads=heads)
    for pointers,tags in itertools.product((0,1,2,7,8,16,32,63),(0,1,7,8,56,63)):yield Case(pointers=pointers,tags=tags,kind=7)
    for own,slot,match in itertools.product((0,2,5),range(6),range(3)):yield Case(owner_node=own,pointers=(1<<slot)if match!=1 else 0,tags=(1<<slot)if match else 0,kind=255)
    for connected,kind,seed,outcome,alias in itertools.product((1,3,5,7),(0,7),SEEDS,(0,1),range(4)):yield Case(connected=connected,kind=kind,seed=seed,outcome=outcome,alias=alias,mutation=3,priority=0xABCDEF81,context=0x80000000)
    for value in(0,0x80000000,1,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345,0x7F7FFFFF):yield Case(kind=7,constants=(value,value^0x80000000,0x404D70A4))
    yield Case(null=1)
