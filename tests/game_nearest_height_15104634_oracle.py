"""Independent full nearest-height contract; private-state matching stays open."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_nearest_height_15104634_recovery as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating

TABLE,BOUND,OPEN,QUERY=0x800D3300,0x800A2370,0x1510F800,0x150A3A70
OFFSETS,VERTICES,OUTPUT,ALT,ACTOR=0x60000,0x70000,0x50000,0x50020,0xA0000
u32=lambda x:x&0xFFFFFFFF
signed=lambda x:((x&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda x:((x&65535)^32768)-32768
add=lambda a,b:bits(floating(a)+floating(b))
sub=lambda a,b:bits(floating(a)-floating(b))
mul=lambda a,b:bits(floating(a)*floating(b))
@dataclass(frozen=True)
class Case:
    count:int=5
    shape:int=0
    height_pattern:int=0
    target:int=0
    x:int=0xC1480000
    z:int=0x41FE0000
    out:int=OUTPUT
    bound:int=0x461C4000
    mutation:int=0
    stages:int=3
    phase:int=0

def cases():
    for n,shape,target in itertools.product((-1,0,1,2,3,4,5,7,8,9,12,16,20,24),range(5),(0,0x80000000,0x42F68000,0x7FC12345)):
        yield Case(count=n,shape=shape,height_pattern=shape%3,target=target)
    for target,height_pattern in itertools.product((0x7F800000,0xFF800000,0x4B000000,0xCB000000,1,0x80000001),range(4)):
        yield Case(target=target,height_pattern=height_pattern)
    for mutation,stages in itertools.product(range(1,32),(1,2,3)):
        yield Case(count=9,mutation=mutation,stages=stages,shape=3)
    for out,phase in itertools.product((OUTPUT,ALT,BOUND),(0,8)):yield Case(out=out,phase=phase,height_pattern=1)
    for n,shape in((0,0),(4,1),(4,2),(-1,0)):yield Case(count=n,shape=shape,out=0)
    for x,z in((0,0x80000000),(0xCF000000,0x4EFFFFFF),(1,0x80000001)):yield Case(x=x,z=z)

def initial_height(c,i):
    return u32((i-12)*257 if c.height_pattern==0 else(-256 if i%2==0 else 256)if c.height_pattern==1 else
               (0x7FFFFFFF,0x80000000,0x12345678,0xEDCBA988)[i%4]if c.height_pattern==2 else(24-i)*1000000)
def triangle(c,i):
    kind=i%3 if c.shape==3 else c.shape
    return((0,0),(0,100),(100,0))if kind==0 else((0,0),(100,0),(0,100))if kind==1 else((0,0),(0,0),(0,0))if kind==2 else((-32768,-32768),(-32768,32767),(32767,-32768))
def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base,n in((TABLE,24*16),(OFFSETS,24*12),(VERTICES,24*64),(OUTPUT,40),(ACTOR,0x32C)):
        m.update({base+i:(i*29+0x5A)&255 for i in range(n)})
    for i in range(24):
        put(m,TABLE+i*16,initial_height(c,i));put(m,TABLE+i*16+4,OFFSETS+i*12);put(m,TABLE+i*16+8,VERTICES+i*64)
        for j,(x,z)in enumerate(triangle(c,i)):
            put(m,OFFSETS+i*12+j*4,j*16);put(m,VERTICES+i*64+j*16,x,2);put(m,VERTICES+i*64+j*16+4,z,2)
    put(m,BOUND,c.bound);put(m,OUTPUT,0xC0A80000);put(m,ALT,0x42A60000)
    put(m,ACTOR+0x14,c.x);put(m,ACTOR+0x18,c.target);put(m,ACTOR+0x1C,c.z);return m
def fields(m):
    result=[]
    for i in range(24):
        result.append(read(m,TABLE+i*16))
        for j in range(3):result.extend((read(m,VERTICES+i*64+j*16,2),read(m,VERTICES+i*64+j*16+4,2)))
    return tuple(result)
def effect(m,c,stage,home):
    flags=c.mutation if c.stages>>stage&1 else 0
    if flags&1:
        for j in range(3):
            p=VERTICES+j*16;x=read(m,p,2);z=read(m,p+4,2);put(m,p,z,2);put(m,p+4,x,2)
    if flags&2:
        for i in range(24):put(m,TABLE+i*16,read(m,TABLE+i*16)^0x80000080)
    if flags&4:put(m,BOUND,0x7FC22222 if stage else 0xBF800000)
    if flags&8:put(m,home+4,bits(31.75+stage))
    if flags&16:put(m,home+12,ALT)
def reference(initial,c):
    m=dict(initial);home=STACK+c.phase;put(m,home+4,c.z);put(m,home+12,c.out);calls=[(OPEN,(0,))]
    effect(m,c,0,home);args=(u32(int(floating(c.x))),u32(int(floating(read(m,home+4)))));calls.append((QUERY,args));effect(m,c,1,home)
    accepted=[]
    for i in range(max(c.count,0)):
        xs=[];zs=[]
        for j in range(3):
            p=u32(read(m,TABLE+i*16+8)+read(m,read(m,TABLE+i*16+4)+j*4));xs.append(bits(float(half(read(m,p,2)))));zs.append(bits(float(half(read(m,p+4,2)))))
        a=sub(xs[0],xs[1]);b=sub(zs[1],zs[0]);intercept=add(mul(zs[0],a),mul(b,xs[0]))^0x80000000
        orientation=add(add(mul(zs[2],a),mul(b,xs[2])),intercept)
        if floating(orientation)>0.0:accepted.append(i)
    if not accepted:return m,calls,0,accepted,-1
    best=read(m,BOUND);nearest=-1
    for i in accepted:
        height=mul(bits(float(signed(read(m,TABLE+i*16)))),0x3B800000);delta=sub(height,c.target)
        if floating(delta)<0.0:delta^=0x80000000
        if floating(delta)<floating(best)or nearest==-1:best=delta;nearest=i
    result=mul(bits(float(signed(read(m,TABLE+nearest*16)))),0x3B800000);put(m,read(m,home+12),result)
    return m,calls,1,accepted,nearest

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=source.SYMS,connected=connected,arguments=(0xAFAFAFAF,0xBFBFBFBF,c.target,c.out)if args is None else args)
        self.f[12],self.f[14]=c.x,c.z;self.f[20:24]=[0x3F123450+i for i in range(4)];self.before_f=self.f[:];self.saved_f=self.f[20:]
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==7:
            self.dispatched_word=word;self.f[word>>6&31]=self.f[word>>11&31]^0x80000000;return
        return super().execute(word)
    def record_call(self,t):
        if t==source.ENTRY:a=(self.f[12],self.f[14],self.r[6],self.r[7])
        else:a=tuple(map(u32,self.arguments({OPEN:1,QUERY:2}[t])))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        stage={OPEN:0,QUERY:1}[t];effect(self.memory,self.case,stage,self.target_home)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.count if t==QUERY else 0xCAFEBABE)
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def check(m,initial,c):
    expected,calls,answer,_,_=reference(initial,c);assert(public(m.memory),m.calls,m.r[2])==(public(expected),calls,answer),c
    assert m.r[29]==STACK+c.phase and m.r[31]==m.before[31]
    assert all(m.r[i]==m.before[i]for i in range(16,24))and m.f[20:24]==m.before_f[20:24]
def guest_checks(p):
    visits=[set(),set()];count=0
    for c in cases():
        initial=fixture(c)
        for i,words in enumerate((p['truth'],p['words'])):
            m=Oracle(words,initial,c).run();check(m,initial,c);visits[i].update((pc-source.ENTRY)//4 for pc in m.visits)
        count+=1
    controls=0
    for at,xor in((0x44,0x04000000),(0x148,2),(0x41C,1),(0x1A0,0x10000),(0x3FC,1)):
        wrong=p['truth'][:];wrong[at//4]^=xor;rejected=False
        for c in(Case(),Case(count=0),Case(shape=1),Case(shape=2),Case(height_pattern=1),Case(target=0x42F68000)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except(AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError):rejected=True;break
        assert rejected,hex(at);controls+=1
    return dict(cases_per_stream=count,streams=2,visited_words=[len(v)for v in visits],unvisited_words=[sorted(set(range(272))-v)for v in visits],effective_instruction_controls=controls,
                complete_public_results_and_providers=True,saved_F20_F22_preserved=True,private_state_and_fault_prefix_relation_not_qualified=True,FCSR_hardware_claim=False)

class WindowEnd(Exception):pass
class WindowCode(dict):
    def __init__(self,inner,end):super().__init__(inner);self.inner=inner;self.end=end;self[end]=0
    def __getitem__(self,pc):
        if pc==self.end:raise WindowEnd
        return self.inner[pc]
def caller_checks(p):
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>21I',rom,0x81188));count=0
    for c in list(cases())[::13]:
        initial=fixture(c);out=STACK+c.phase+0xB4;put(initial,out,bits(-12.0));target=add(c.target,bits(50.0));cc=replace(c,out=out,target=target)
        expected,calls,answer,_,_=reference(initial,cc)
        if answer:
            minimum=add(read(expected,out),bits(50.0))
            if floating(read(expected,ACTOR+0x18))<floating(minimum):put(expected,ACTOR+0x18,minimum)
        for words in(p['truth'],p['words']):
            code=dict(zip(range(source.ENTRY,source.ENTRY+1088,4),words));m=Oracle(window,initial,cc,entry=0x15053CD8,connected=code);m.r[16]=ACTOR;m.f[8]=bits(50.0);m.code=WindowCode(m.code,0x15053D2C)
            try:m.run();raise AssertionError('Unfired original caller continuation')
            except WindowEnd:pass
            assert(m.calls,public(m.memory),read(m.memory,out))==([(source.ENTRY,(cc.x,cc.z,cc.target,out)),*calls],public(expected),read(expected,out)),c
            assert m.r[29]==STACK+c.phase and m.r[16]==ACTOR and m.f[20:24]==m.before_f[20:24]
        count+=1
    return dict(original_window_words=21,scenarios=count,streams=2,F12_F14_A2_A3_checked=True,actor_height_clamp_checked=True,full_parent_or_hardware_claim=False)
