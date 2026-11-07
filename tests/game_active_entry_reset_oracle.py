"""Independent byte-memory reset loop and retained SDK helper execution."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ENTRY,CONFIG,RANDOM,ZERO=0x15191400,0x1513F680,0x150ADA20,0x100226F0
TABLE,SEED=0x800A9D40,0x800885B0
OWNER,OTHER,LIST,ALTERNATE,MARK=0x30000,0x31000,0x60000,0x61000,0x70000
ACTORS=(0x50000,0x50400,0x50800,0x50C00)
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    pattern:int=1
    selector:int=3
    base:int=-32768
    span:int=32767
    random:int=0xFFFFFFFF
    mutation:int=0
    alias:int=0
    phase:int=0
    connected:int=0
    seed:int=1
def symbols():return dict(D_800A9D40=TABLE,func_1513F680=CONFIG,func_150ADA20=RANDOM,bzero=ZERO)
def addresses(c):
    actors=(LIST+0x240,*ACTORS[1:])if c.alias==4 else (LIST-28,0xFFE4,*ACTORS[2:])if c.alias==5 else ACTORS
    owner=actors[0]+0x20 if c.alias==1 else OWNER
    entries=actors[0]+0x100 if c.alias==2 else TABLE+0x1000 if c.alias==3 else LIST
    return owner,entries,actors
def active(c):return ((),(0,),(59,),tuple(range(0,60,2)),tuple(range(60)),(0,3,59))[c.pattern]
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[p+i]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[p+i]=b
def fixture(c=Case(),order='big'):
    owner,entries,actors=addresses(c);m={STACK+c.phase+i:(i*17+165)&255 for i in range(-512,256)}
    for p,n in((OWNER,128),(OTHER,128),(LIST,768),(ALTERNATE,768),(TABLE,5120),(MARK,16),*[(a,512)for a in actors]):
        for i in range(n):m[p+i]=(i*29+90)&255
    for i in range(256):wr(m,TABLE+i*20,c.base,2,order);wr(m,TABLE+i*20+2,c.span,2,order)
    for i in range(60):wr(m,entries+i*12,0,4,order)
    for i in active(c):wr(m,entries+i*12,actors[0 if c.pattern==5 else i%4],4,order)
    for j,a in enumerate(actors):
        for k in range(3):wr(m,a+0x110+k*4,0x3F800000+(j+k)*0x10000,4,order)
        wr(m,a+0x1C,actors[0]>>16 if c.alias==5 and j==0 else 0x8123+j,2,order)
        wr(m,a+0x58,0 if c.alias==5 and j==0 else 0xA5A50000+j*2,4,order);m[a+0x130]=0 if c.alias in(2,5)else c.selector
    for a,p in((owner,entries),(OTHER,ALTERNATE)):
        wr(m,a+0x1C,0x80000000,4,order);wr(m,a+0x20,0x01234567,4,order);wr(m,a+0x24,p,4,order)
    wr(m,SEED,c.seed,8,order);return m
def effect(m,c,stage,number,actor,home,order='big'):
    if number:return
    owner,entries,actors=addresses(c);first=active(c)[0]if active(c)else 0
    if stage==0:
        if c.mutation&1:wr(m,entries+first*12,actors[1],4,order)
        if c.mutation&2:wr(m,TABLE+c.selector*20,-32768,2,order);wr(m,TABLE+c.selector*20+2,32767,2,order);m[actor+0x130]=255
        if c.mutation&4:wr(m,owner+0x24,ALTERNATE,4,order)
        if c.mutation&8:wr(m,home,OTHER,4,order)
    else:
        # A guest-only timer/entry-pointer overlap. The bounded RNG clears
        # the future slot touched by the authentic configuration byte stores.
        if c.alias==5:wr(m,entries+7*12,0,4,order)
        if c.mutation&16:wr(m,entries+first*12,actors[2],4,order)
        if c.mutation&32:wr(m,TABLE+c.selector*20,32767,2,order);wr(m,TABLE+c.selector*20+2,0,2,order)
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-512<=p<STACK+c.phase+256}
def reference(initial,c=Case(),home=None,order='big'):
    owner,unused,actors=addresses(c);home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];number=0
    wr(m,home,owner,4,order);wr(m,owner+0x1C,0,4,order);wr(m,owner+0x20,0,4,order);entries=rd(m,owner+0x24,4,order)
    for i in range(60):
        slot=entries+i*12;actor=rd(m,slot,4,order)
        if not actor:continue
        preset=TABLE+m[actor+0x130]*20
        for k in range(3):wr(m,actor+0x110+k*4,0,4,order)
        actor=rd(m,slot,4,order);calls.append((CONFIG,(actor,13,18,0,13)))
        for off,v in enumerate((13,18,0,13)):m[actor+0x70+off]=v
        if not c.connected&1:effect(m,c,0,number,actor,home,order)
        calls.append((RANDOM,()))
        if c.connected&2:value=next_seed(rd(m,SEED,8,order));wr(m,SEED,value,8,order);value=u32(value)
        else:effect(m,c,1,number,actor,home,order);value=u32(c.random+number*0x9E3779B9)
        divisor=u32(half(rd(m,preset+2,2,order))+1);assert divisor,'Zero-divisor hardware effects outside this reference'
        base=half(rd(m,preset,2,order));actor=rd(m,slot,4,order);wr(m,actor+0x1C,value%divisor+base,2,order)
        actor=rd(m,slot,4,order);wr(m,actor+0x58,rd(m,actor+0x58,4,order)|1,4,order);number+=1
    owner=rd(m,home,4,order);dest=rd(m,owner+0x24,4,order);calls.append((ZERO,(dest,720)))
    for i in range(720):m[dest+i]=0
    return dict(memory=public(m,c),calls=calls,random_calls=number)
class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,home=None):
        self.s=symbols();self.number=0;self.config_number=0;self.home=STACK+c.phase if home is None else home
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(addresses(c)[0],))
    def record_call(self,t):
        counts={ENTRY:1,CONFIG:5,RANDOM:0,ZERO:2,0x15169804:1,0x15169824:1};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xA5000002
        if t==CONFIG:
            for off,v in enumerate(a[1:]):self.memory[a[0]+0x70+off]=v
            effect(self.memory,c,0,self.config_number,a[0],self.home);self.config_number+=1
        elif t==RANDOM:
            effect(self.memory,c,1,self.number,0,self.home);value=u32(c.random+self.number*0x9E3779B9);self.number+=1
        elif t==ZERO:
            assert a[1]==720
            for i in range(a[1]):self.memory[a[0]+i]=0
        elif t in(0x15169804,0x15169824):wr(self.memory,MARK,a[0]);value=0x13579BDF
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helpers(rom,c):
    code={}
    for bit,entry,offset,n in((1,CONFIG,0x16CB30,16),(2,RANDOM,0xDAED0,18),(4,ZERO,0x226F0,40)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for selector in range(256):yield Case(selector=selector)
    for pattern,base,span,random in itertools.product(range(6),(-32768,-1,0,32767),(-32768,-2,0,1,32767),(0,0x80000000,0xFFFFFFFF)):
        yield Case(pattern=pattern,base=base,span=span,random=random)
    for mutation,phase in itertools.product(range(64),(0,8)):yield Case(pattern=5,mutation=mutation,phase=phase)
    for alias,pattern in itertools.product(range(1,5),(1,5)):yield Case(alias=alias,pattern=pattern)
    yield Case(alias=5,base=0,span=0,random=0)
