"""Two live owner channels, ordered samples and original helper connections."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.test_game_ribbon_effect_constructor_match import lookup
ENTRY,INTEGER,FLOAT,ANGLE,CREATE,ALLOCATE,COPY=0x1518BD60,0x150ADA20,0x150ADA68,0x151423D8,0x15147DA0,0x15147A80,0x10022EC0
RECORD,OWNER,OTHER,CREATED,PAYLOAD=0x320000,0x330000,0x331000,0x340000,0x350000
TICK,THRESHOLD,TABLE,SEED,UNIT=0x800BE9E4,0x800A7440,0x8009A220,0x800885B0,0x8009F740
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
data=lambda m,p,n:bytes(m[u32(p+i)]for i in range(n))
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
LOOKUP=()
@dataclass(frozen=True)
class Case:
    timers:tuple=(-1,-1)
    tick:int=1
    gate:int=0
    tag:int=37
    limits:tuple=(5,55)
    randoms:tuple=(0xFFFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF,129,23,255,21)
    fractions:tuple=(bits(.25),bits(.75),bits(.5),bits(.125))
    values:tuple=(bits(10.),bits(10.),bits(10.),bits(10.))
    threshold:int=0x3F276C8B
    metric:int=65
    kind:int=5
    flags:int=19
    category:int=255
    context:int=129
    outcome:int=3
    mutation:int=0
    alias:int=0
    connected:int=0
    phase:int=0
    seed:int=1

def symbols():return dict(D_800BE9E4=TICK,D_800A7440=THRESHOLD,func_150ADA20=INTEGER,func_150ADA68=FLOAT,func_151423D8=ANGLE,func_15147DA0=CREATE)
def result(i):return CREATED+i*0x1000
def payload(c,i):return RECORD+0x24-0x48 if c.alias==1 else RECORD+0x30-0x48 if c.alias==2 else PAYLOAD+i*0x1000
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-1024,256)}
    for p,n in((RECORD-128,768),(OWNER,512),(OTHER,512),(CREATED,512),(CREATED+4096,512),(PAYLOAD,128),(PAYLOAD+4096,128)):
        m.update({p+i:(i*7+c.seed*11+90)&255 for i in range(n)})
    for base,k in((OWNER,0),(OTHER,1),(RECORD,2)):
        put(m,base,1);put(m,base+0x1D4,1);m[base+59]=c.tag&255;put(m,base+0x184,c.metric+k)
        for i in range(2):
            put(m,base+0x1AC+6*i,(-32768+71*k+19*i)&65535,2);put(m,base+0x1B0+6*i,(32767-79*k-23*i)&65535,2)
    m[RECORD]=31;m[RECORD+1]=c.context&255;m[RECORD+12]=c.category&255
    for i,v in enumerate(c.values):put(m,RECORD+16+4*i,v)
    for i,v in enumerate(c.limits):put(m,RECORD+32+2*i,v,2)
    put(m,RECORD+36,0 if c.gate==1 else OWNER);m[RECORD+40]=c.tag&255;m[RECORD+41]=c.kind&255;m[RECORD+42]=c.flags&255
    if c.gate==2:put(m,OWNER,0)
    if c.gate==3:put(m,OWNER+0x1D4,0)
    if c.gate==4:m[OWNER+59]^=1
    for i,v in enumerate(c.timers):put(m,RECORD+44+4*i,v)
    for i in range(2):put(m,result(i)+0x98,payload(c,i))
    put(m,s['D_800BE9E4'],c.tick);put(m,s['D_800A7440'],c.threshold)
    for i,v in enumerate(LOOKUP):put(m,TABLE+4*i,v)
    put(m,SEED,c.seed,8);put(m,UNIT,0x37800080);return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+256}
def effect(m,c,s,stage,number,request=None):
    if stage==INTEGER and number==0 and c.mutation&1:put(m,RECORD+34,7,2)
    if stage==FLOAT and number==0 and c.mutation&2:put(m,RECORD+16,bits(-3.));put(m,RECORD+20,bits(2.))
    if stage==FLOAT and number==1 and c.mutation&4:
        put(m,RECORD+24,bits(17.));put(m,RECORD+28,bits(-.5));m[RECORD+41]=211;m[RECORD+42]=255;m[RECORD+1]=255;m[RECORD+12]=129
    if stage in(CREATE,ALLOCATE)and c.mutation&8:
        put(m,RECORD+36,OTHER);put(m,s['D_800BE9E4'],7);put(m,s['D_800A7440'],0x7FC12345)
        if request is not None:put(m,request,bits(1.25+number))

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];packets=[];ni=nf=nc=0;home=STACK+c.phase;req,desc,render=home-36,home-68,home-104;threshold=read(m,s['D_800A7440'])
    def integer():
        nonlocal ni
        calls.append((s['func_150ADA20'],()))
        if c.connected&1:v=next_seed(read(m,SEED,8));put(m,SEED,v,8)
        else:effect(m,c,s,INTEGER,ni);v=c.randoms[ni]
        ni+=1;return u32(v)
    def fraction():
        nonlocal nf
        calls.append((s['func_150ADA68'],()))
        if c.connected&2:v=next_seed(read(m,SEED,8));put(m,SEED,v,8);v=mul(bits(float(v&65535)),read(m,UNIT))
        else:effect(m,c,s,FLOAT,nf);v=c.fractions[nf]
        nf+=1;return u32(v)
    for i in range(2):
        timer=RECORD+44+4*i;remaining=u32(read(m,timer)-read(m,s['D_800BE9E4']));put(m,timer,remaining);owner=read(m,RECORD+36)
        if not(owner and read(m,owner)and read(m,owner+0x1D4)and m[RECORD+40]==m[owner+59]):continue
        if remaining&0x80000000:
            angle=integer()%u32(half(read(m,RECORD+34,2))+1);calls.append((s['func_151423D8'],(angle&255,)));first=lookup(angle,LOOKUP);calls.append((s['func_151423D8'],((angle-64)&255,)));quarter=lookup(angle-64,LOOKUP)
            f=fraction();speed=add(mul(f,read(m,RECORD+20)),read(m,RECORD+16));put(m,timer,integer()%23+5)
            for off,v in enumerate((0,1,0x160600,3,16,128,32)):put(m,render+off*4,v)
            m[render+28]=0;m[render+29]=9
            n=integer()%u32(half(read(m,RECORD+32,2))+1);m[req+21]=(n+3)&255;put(m,req+16,1);put(m,req+14,1,2);put(m,req+12,integer()%21+80,2);m[desc+25]=m[RECORD+41]
            f=fraction();gravity=add(mul(f,read(m,RECORD+28)),read(m,RECORD+24))
            for j,v in enumerate((gravity,mul(speed,quarter),0,mul(speed,first),threshold)):put(m,desc+4*j,v)
            m[desc+24]=m[RECORD+42]|8;m[desc+26]=u32(255-((read(m,read(m,RECORD+36)+0x184)>>5)<<6))&255;m[desc+27]=255
            args=(req,desc,m[req+21]*12+8,5,1,0,2,1,0,0,0,render,0,m[RECORD+12],m[RECORD+1]);calls.append((s['func_15147DA0'],args));packets.append((data(m,req,28),data(m,desc,32),data(m,render,32)))
            answer=result(nc)if c.outcome>>nc&1 else 0
            if c.connected&8:
                put(m,req+16,1);a=(req,args[2]+72,20,1,0,1,0,0,0,args[13],args[14]);calls.append((ALLOCATE,a));effect(m,c,s,ALLOCATE,nc,req)
                if answer:
                    p=read(m,answer+0x98);calls.append((COPY,(p,desc,32)))
                    for j,v in enumerate(data(m,desc,32)):m[p+j]=v
                    for j,v in enumerate((5,1,0,2,1,0)):m[p+32+j]=v
                    for j,v in enumerate(data(m,render,32)):m[p+40+j]=v
            else:effect(m,c,s,CREATE,nc,req)
            if answer:p=read(m,answer+0x98)+72;put(m,p,RECORD);m[p+4]=i
            nc+=1;owner=read(m,RECORD+36)
        put(m,RECORD+52+4*i,bits(float(half(read(m,owner+0x1AC+6*i,2)))))
        put(m,RECORD+60+4*i,bits(float(half(read(m,read(m,RECORD+36)+0x1B0+6*i,2)))))
    return dict(memory=m,calls=calls,packets=packets,integers=ni,floats=nf,factories=nc)

class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments_override=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.packets=[];self.ni=self.nf=self.nc=0
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(RECORD,)if arguments_override is None else arguments_override)
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==7:
            # NEG.S of the retained finite quarter-wave table toggles its sign.
            self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
        else:super().execute(word)
    def record_call(self,t):
        counts={ENTRY:1,self.s['func_150ADA20']:0,self.s['func_150ADA68']:0,self.s['func_151423D8']:1,self.s['func_15147DA0']:15,ALLOCATE:11,COPY:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==self.s['func_150ADA20']:self.ni+=1
        if t==self.s['func_150ADA68']:self.nf+=1
        if t==self.s['func_15147DA0']:
            self.nc+=1;self.packets.append((data(self.memory,a[0],28),data(self.memory,a[1],32),data(self.memory,a[11],32)))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xA5000002;fv=None
        if t==self.s['func_150ADA20']:effect(self.memory,c,self.s,INTEGER,self.ni-1);value=c.randoms[self.ni-1]
        elif t==self.s['func_150ADA68']:effect(self.memory,c,self.s,FLOAT,self.nf-1);fv=c.fractions[self.nf-1]
        elif t==self.s['func_151423D8']:fv=lookup(a[0],LOOKUP)
        elif t in(self.s['func_15147DA0'],ALLOCATE):
            effect(self.memory,c,self.s,CREATE if t==self.s['func_15147DA0']else ALLOCATE,self.nc-1,a[0]);value=result(self.nc-1)if c.outcome>>(self.nc-1)&1 else 0
        elif t==COPY:
            assert a[2]==32
            for i,v in enumerate(data(self.memory,a[1],32)):self.memory[a[0]+i]=v
            value=a[0]
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
        if fv is not None:self.f[0]=fv
def helper_code(rom,c,s=None):
    s=symbols()if s is None else s;code={}
    for bit,entry,offset,n in((1,s['func_150ADA20'],0xDAED0,18),(2,s['func_150ADA68'],0xDAF18,25),(4,s['func_151423D8'],0x16F888,27),(8,s['func_15147DA0'],0x175250,70),(16,COPY,0x22EC0,11)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.packets,m.ni,m.nf,m.nc)
def cases():
    for angle,timers,outcome in itertools.product(range(256),((-1,-1),(-1,100),(100,-1),(100,100)),(0,3)):
        yield Case(randoms=(angle,0xFFFFFFFF,0x80000000,0xFFFFFFFE,angle+64,23,255,21),timers=timers,outcome=outcome,kind=angle,flags=angle^0xA5,metric=u32(angle*0x1020304),category=angle,context=angle^0xFF)
    for gate,timers,tick in itertools.product(range(5),((0,0),(0x80000000,0x7FFFFFFF),(0xFFFFFFFF,1)),(0,1,0xFFFFFFFF)):yield Case(gate=gate,timers=timers,tick=tick)
    for first,second in itertools.product((-32768,-2,0,1,32767),repeat=2):yield Case(limits=(first,second))
    for mutation,outcome,alias in itertools.product((0,1,2,4,8,15),range(4),range(3)):yield Case(mutation=mutation,outcome=outcome,alias=alias,phase=8)
    for connected,seed,outcome in itertools.product((1,3,7,8,15,31),SEEDS,(0,1,3)):yield Case(connected=connected,seed=seed,outcome=outcome,mutation=8)
