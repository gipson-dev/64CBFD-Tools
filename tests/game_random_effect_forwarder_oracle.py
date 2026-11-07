"""Five ordered draws, rounded float payload, original RNGs and caller windows."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_random_effect_forwarder_candidates as source
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ENTRY,FLOAT,INTEGER,SUBMIT=source.ENTRY,0x150ADA68,0x150ADA20,0x15102B38
FACTORY,COPY,FOLLOWUP=0x1513D2F0,0x10022EC0,0x15103254
OWNER,POSITION,OUTPUT,MARK=0x30000,0x60000,0x50000,0x70000
SEED,UNIT,TEMPLATE=0x800885B0,0x8009F740,0x800A5480
GLOBALS=(0x800AAABC,0x800AAAC0,0x800AAAC4,0x800AAAC8)
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
@dataclass(frozen=True)
class Case:
    floats:tuple=(0x3E800000,0x3F000000,0x3F400000)
    integers:tuple=(0xFFFFFFFF,0x80000000)
    constants:tuple=(0x42800000,0x3F000000,0x40000000,0xC1F00000)
    duration:int=0xABCD8001
    priority:int=0x123456FF
    parameter:int=0x87654321
    mutation:int=0
    outcome:int=1
    owner:int=OWNER
    phase:int=0
    seed:int=0x123456789ABCDEF0
    connected:int=0
    alias:int=0
    position:int=POSITION

def symbols():
    return{n:int(n.split('_')[1],16)for n in('func_150ADA68','func_150ADA20','func_15102B38','D_800AAABC','D_800AAAC0','D_800AAAC4','D_800AAAC8','D_800AAA90','D_800AAA9C')}
def args(c):return tuple(map(u32,(c.owner,c.position,c.duration,c.priority,c.parameter)))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+165)&255 for i in range(-1024,2304)}
    for p,n in((OWNER,0x80),(POSITION,32),(OUTPUT,0x200),(MARK,4),(TEMPLATE,12)):
        m.update({p+i:(i*29+89)&255 for i in range(n)})
    for k,v in zip(('D_800AAABC','D_800AAAC0','D_800AAAC4','D_800AAAC8'),c.constants):put(m,s[k],v)
    for base in(s['D_800AAA90'],s['D_800AAA9C']):
        for i,v in enumerate((0x3F800000,0x40000000,0x40400000)):put(m,base+4*i,v)
    for i in range(3):put(m,c.position+4*i,bits(10.+i))
    put(m,SEED,c.seed,8);put(m,UNIT,0x37800000);put(m,MARK,0)
    put(m,STACK+c.phase+16,c.parameter)
    return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+2304}
def effect(m,c,s,n,home):
    put(m,MARK,n)
    if c.mutation&1:
        for i,k in enumerate(('D_800AAABC','D_800AAAC0','D_800AAAC4','D_800AAAC8')):put(m,s[k],bits((n+i+1)*0.25))
    if c.mutation&2:
        if c.owner:m[c.owner]=(n*17)&255
        for i in range(3):put(m,c.position+4*i,bits(float(n*10+i)))
    if c.mutation&4:
        for i,k in enumerate(('D_800AAA90','D_800AAA9C')):
            for j in range(3):put(m,s[k]+4*j,bits(float(n+i+j)))
    if c.alias:
        # Intentional guest-only writes to the caller's private homes.
        p=home+(-20,-16,-12,0,4,8,12,16)[c.alias-1]
        put(m,p,(OWNER if c.alias==4 else POSITION if c.alias==5 else 0x12348000+n))
def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];draws=[];fi=ii=0
    def draw(kind):
        nonlocal fi,ii
        n=len(draws)+1;calls.append((s[kind],()));effect(m,c,s,n,home)
        if c.connected:
            seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8);v=mul(bits(float(seed&65535)),read(m,UNIT))if kind=='func_150ADA68'else u32(seed)
        elif kind=='func_150ADA68':v=c.floats[fi];fi+=1
        else:v=c.integers[ii];ii+=1
        draws.append(v);return v
    first=mul(add(mul(draw('func_150ADA68'),read(m,s['D_800AAABC'])),bits(604.)),read(m,s['D_800AAAC0']))
    second=mul(add(mul(draw('func_150ADA68'),bits(59.)),bits(141.)),read(m,s['D_800AAAC4']))
    kind=(draw('func_150ADA20')&3)+6;draw('func_150ADA20')
    angle=add(mul(draw('func_150ADA68'),bits(270.)),read(m,s['D_800AAAC8']))
    a=(u32(c.owner),0,s['D_800AAA90'],s['D_800AAA9C'],home-8,kind,255,angle,c.position,255,0,u32(half(c.duration)),c.priority&255,u32(c.parameter));calls.append((s['func_15102B38'],a))
    pair=(second,first);templates=tuple(read(m,s[k]+4*j)for k in('D_800AAA90','D_800AAA9C')for j in range(3))
    return dict(memory=m,calls=calls,pair=pair,templates=templates,result=OUTPUT if c.outcome and c.owner else 0,draws=draws)

class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.n=self.fi=self.ii=0;self.payloads=[];self.factory_packets=[];self.home=STACK+c.phase;self.original=dict(memory)
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=args(c)if arguments is None else arguments)
    def record_call(self,t):
        counts={self.s['func_150ADA68']:0,self.s['func_150ADA20']:0,self.s['func_15102B38']:14,ENTRY:5,FACTORY:12,COPY:3,FOLLOWUP:7}
        assert t in counts,hex(t);a=tuple(u32(v)for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t in(self.s['func_150ADA68'],self.s['func_150ADA20']):
            self.n+=1
            if self.n<=5:effect(self.memory,self.case,self.s,self.n,self.home)
        if t==self.s['func_15102B38']:
            self.payloads.append((tuple(read(self.memory,a[4]+4*i)for i in range(2)),tuple(read(self.memory,a[k]+4*i)for k in(2,3)for i in range(3))))
        if t==FACTORY:self.factory_packets.append(bytes(self.memory[a[0]+i]for i in range(80)))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];float_value=None
        if t==self.s['func_150ADA68']:float_value=c.floats[self.fi];self.fi+=1;value=0xA5000002
        elif t==self.s['func_150ADA20']:value=c.integers[self.ii%2];self.ii+=1
        elif t in(self.s['func_15102B38'],FACTORY):value=OUTPUT if c.outcome and c.owner else 0
        elif t==COPY:
            assert a[2]==48;data=bytes(self.memory[a[1]+i]for i in range(a[2]))
            for i,b in enumerate(data):self.memory[a[0]+i]=b
            value=a[0]
        else:assert t==FOLLOWUP;value=0x81234567
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(value);self.hi,self.lo=0xA5000010,0xA5000011
        if float_value is not None:self.f[0]=float_value

def helper_code(rom,c):
    code={}
    for entry,offset,n,enabled in((INTEGER,0xDAED0,18,c.connected),(FLOAT,0xDAF18,25,c.connected),(SUBMIT,0x12FFE8,134,c.connected==2)):
        if enabled:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def cases():
    for i in range(256):yield Case(duration=0xABCD0000|i*257,priority=0x12340000|i,integers=(u32(i*1234567),u32(~i)),mutation=i%8,outcome=i%2,phase=(i%2)*8)
    for value,phase,mutation,outcome in itertools.product((0,1,2,3,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,8),(0,7),(0,1)):yield Case(duration=value,priority=value,parameter=value,mutation=mutation,outcome=outcome,phase=phase,integers=(value,u32(~value)))
    for sample in(0,0x80000000,1,0x3F800000,0xBF800000,0x7F7FFFFF,0x7FC12345,0x7F800000,0xFF800000):yield Case(floats=(sample,sample,sample))
    for seed,phase,outcome in itertools.product(SEEDS,(0,8),(0,1)):yield Case(seed=seed,phase=phase,outcome=outcome,connected=1)
    for owner in(0,OWNER):yield Case(owner=owner,mutation=7)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.payloads,m.factory_packets)

def caller_machine(rom,words,c=Case(),which=0):
    start,count,end=(0x150288B0,7,0x150288CC)if which==0 else(0x151C537C,6,0x151C5394)
    if which:c=replace(c,position=STACK+c.phase+0xD4)
    initial=fixture(c);code=helper_code(rom,c);code.update(zip(range(ENTRY,ENTRY+284,4),words));code[end]=0
    offset=start-0x15000000+0x2D4B0;body=struct.unpack_from('>%dI'%count,rom,offset);m=Oracle(body,initial,c,entry=start,connected=code,arguments=())
    m.r[4]=m.before[4]=c.owner;m.r[16]=m.before[16]=POSITION if which==0 else c.owner
    for p,n,v in((m.r[29]+0x773,1,c.priority),(m.r[29]+0xE7,1,c.priority),(m.r[29]+0xE8,4,c.parameter)):put(m.memory,p,v,n)
    m.code=WindowCode(m.code,m);m.code.ends=(end,);return m
