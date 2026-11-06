"""Ordered clear/default protocol, opaque effects and original leaf helpers."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_object_defaults_candidates as candidate
from tools.experiments import game_object_defaults_match as source
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
RANDOM,COMPONENT,ADAPTER,PARENT=0x150ADA20,0x150615DC,0x1505C7D8,0x1505D1C4
OTHER,THIRD,MARK=0x31000,0x32000,0x70000
u32=lambda x:x&0xFFFFFFFF
FLOATS=(0,0x80000000,0x3F800000,0xC61C4000,0x40533333,1,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345)
RANDOMS=(0,1,49,50,51,99,100,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
@dataclass(frozen=True)
class Case:
    random:int=0xFFFFFFFF
    base:int=0xC61C4000
    gravity:int=0x40533333
    mutation:int=0
    connected:bool=False
    component:bool=True
    seed:int=0x123456789ABCDEF0
    phase:int=0
    owner:int=0x30000
    redirect:int=0
    pattern:int=0

def symbols():return dict(D_8009962C=0x8009962C,D_80099630=0x80099630,func_150ADA20=RANDOM,func_150615DC=COMPONENT,D_800885B0=0x800885B0)
def block(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165+c.pattern*7)&255 for i in range(-0x600,0x500)}
    for j,p in enumerate((c.owner,OTHER,THIRD)):
        m.update({u32(p+i):(i*29+j*31+123+c.pattern*71)&255 for i in range(-16,0x33C)})
    for p in(s['D_8009962C'],s['D_80099630'],s['D_800885B0']):
        for i in range(-8,16):m.setdefault(u32(p+i),(i*31+77)&255)
    put(m,s['D_8009962C'],c.base);put(m,s['D_80099630'],c.gravity);put(m,s['D_800885B0'],c.seed,8)
    m[0x800C3E78]=0xE1
    for i in range(3):put(m,MARK+4*i,0)
    return m

def effect(m,c,s,phase,owner,home):
    if phase==0 and c.mutation&1:
        put(m,u32(owner+0x48),0xFFC12345);put(m,s['D_8009962C'],0x80000000);put(m,s['D_80099630'],0x7FC54321)
    elif phase==1 and c.mutation&2:
        put(m,u32(owner+0x14C),0x80000000);put(m,u32(owner+0x18C),0xFFFFFFFF);put(m,u32(owner+0x19C),0xBEEF,2);m[u32(owner+0x1DD)]=0x31
    if c.redirect&(1<<phase):put(m,home,(OTHER,THIRD)[phase])
    put(m,MARK+phase*4,0xA5000000+phase)

def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;m=dict(initial);trace=[];calls=[];observations=[];home=STACK+c.phase if home is None else home;p=c.owner
    def load(a,n):
        a=u32(a);v=read(m,a,n);trace.append(('R',a,n,v));return v
    def store(a,v,n):
        a=u32(a);assert all(a+i in m for i in range(n));put(m,a,v,n);trace.append(('W',a,n,v&((1<<(8*n))-1)))
    cursor=p;end=u32(p+0x32C)
    while cursor<end:store(cursor,0,4);cursor=u32(cursor+4)
    base=load(s['D_8009962C'],4)
    for at,v,n in((0x2FD,2,1),(0x38,0xD8F0,2),(0x14C,0x3F800000,4),(0x150,0x3F800000,4),(0x118,base,4),(0x180,base,4)):store(p+at,v,n)
    gravity=load(s['D_80099630'],4)
    for at,v,n in((0x1DC,255,1),(0x127,255,1),(0x84,65535,2),(0x13F,255,1),(0x2C4,u32(p+4),4),(0x2C8,1,1),(0x2C9,1,1),(4,255,1),(0x2CB,50,1),(0x48,0x3F800000,4),(0x24,gravity,4)):store(p+at,v,n)
    calls.append((s['func_150ADA20'],()));observations.append((s['func_150ADA20'],p,block(m,p,0x32C)))
    effect(m,c,s,0,p,home)
    value=c.random
    if c.connected:value=next_seed(read(m,s['D_800885B0'],8));put(m,s['D_800885B0'],value,8)
    if c.redirect&1:p=OTHER
    store(p+0x6E,u32(value)%50+50,1)
    calls.append((s['func_150615DC'],(p,)));observations.append((s['func_150615DC'],p,block(m,p,0x32C)));effect(m,c,s,1,p,home)
    if c.component:
        for at,v in((7,255),(8,255),(9,0),(10,0),(15,0),(14,255),(13,255),(12,255),(11,255)):store(p+at,v,1)
    if c.redirect&2:p=THIRD
    for at,v,n in((0x1DD,255,1),(0x1DE,255,1),(0x1DF,255,1),*[(at,0,2)for at in(0x18C,0x18E,0x190,0x192,0x194)],(0x196,10,2),(0x198,10,2),(0x19A,0,2),(0x19C,0,2)):store(p+at,v,n)
    return dict(memory=m,trace=trace,calls=calls,observations=observations)

def public(m):return{p:v for p,v in m.items()if not STACK-0x600<=p<STACK+0x500}
class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.number=0
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.owner,)if arguments is None else arguments)
        self.semantic_trace=[]
    def get(self,p,n):
        if self.own_instruction:assert p%n==0,('unaligned read',p,n)
        v=super().get(p,n)
        if self.own_instruction and not self.s['func_150ADA20']<=self.current_pc<self.s['func_150ADA20']+72 and not STACK-0x600<=p<STACK+0x500:self.semantic_trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        if self.recording and self.own_instruction:
            assert p%n==0,('unaligned write',p,n)
            assert all(p+i in self.memory for i in range(n)),('unmapped write',p,n)
        super().put(p,v,n)
        if self.recording and self.own_instruction and not self.s['func_150ADA20']<=self.current_pc<self.s['func_150ADA20']+72 and not STACK-0x600<=p<STACK+0x500:self.semantic_trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        counts={source.ENTRY:1,self.s['func_150ADA20']:0,self.s['func_150615DC']:1,ADAPTER:2};assert t in counts,hex(t)
        args=tuple(u32(a)for a in self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t in(self.s['func_150ADA20'],self.s['func_150615DC']):
            phase=0 if t==self.s['func_150ADA20']else 1;p=self.case.owner if phase==0 else args[0]
            self.observations.append((t,p,block(self.memory,p,0x32C)));effect(self.memory,self.case,self.s,phase,p,self.r[29]+24)
        elif t==ADAPTER:
            self.observations.append((t,args[0],block(self.memory,args[0],0x32C),self.memory[0x800C3E78]))
    def hook(self,t):
        if t==self.s['func_150ADA20']:value=self.case.random
        elif t==self.s['func_150615DC']:value=0x87654321
        else:
            assert t==ADAPTER;self.memory[0x800C3E78]=0xFE;put(self.memory,self.calls[-1][1][0]+0x24,0xC2400000);value=0x76543210;put(self.memory,MARK+8,0xA5000002)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def helper_code(rom,c):
    code={}
    for entry,off,n,enabled in((RANDOM,0xDAED0,18,c.connected),(COMPONENT,0x8EA8C,12,c.component)):
        if enabled:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
    return code

def bound(obj,s,fitted=False):
    raw,bindings=source.function_blob(obj)
    if fitted:raw=source.normalized(raw,bindings,(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM+source.SIZE])
    original=list(struct.unpack('>%dI'%(len(raw)//4),raw));words=original[:];pending={}
    for at,rows in sorted(bindings.items()):
        assert len(rows)==1;kind,name=rows[0];value=s[name];w=original[at//4]
        if kind=='R_MIPS_HI16':pending.setdefault(name,[]).append(at)
        elif kind=='R_MIPS_LO16':
            low=((w&65535)^32768)-32768
            for hi in pending.pop(name,()):
                addend=((original[hi//4]&65535)<<16)+low;words[hi//4]=(original[hi//4]&0xFFFF0000)|(((value+addend+32768)>>16)&65535)
            words[at//4]=(w&0xFFFF0000)|((value+low)&65535)
        else:
            assert kind=='R_MIPS_26';words[at//4]=(w&0xFC000000)|(((value+((w&0x3FFFFFF)<<2))>>2)&0x3FFFFFF)
    assert not pending;return words

def cases():
    for base,gravity,mutation,phase in itertools.product(FLOATS,FLOATS,(0,3),(0,8)):yield Case(base=base,gravity=gravity,mutation=mutation,phase=phase,component=bool(base&1))
    for value,component,phase in itertools.product((*range(50),*RANDOMS),(False,True),(0,8)):yield Case(random=value,component=component,phase=phase)
    for seed,component,phase in itertools.product(SEEDS,(False,True),(0,8)):yield Case(seed=seed,connected=True,component=component,phase=phase)

def controls():
    b=candidate.SELECTED
    return dict(short_clear=b.replace('+ 0x32C','+ 0x328'),long_clear=b.replace('+ 0x32C','+ 0x330'),skip_first=b.replace('u32 *cursor = (u32 *)object','u32 *cursor = (u32 *)object + 1'),
      state_byte=b.replace('[0x2FD] = 2','[0x2FD] = 1'),wrong_half=b.replace('= -10000;','= -9999;'),wrong_unit=b.replace('unit = 1.0f','unit = 2.0f'),
      wrong_base=b.replace('base = D_8009962C','base = D_80099630'),wrong_gravity=b.replace('gravity = D_80099630','gravity = D_8009962C'),wrong_pointer=b.replace('= (u8 *)object + 4;','= (u8 *)object + 8;'),
      wrong_ID=b.replace('unk84.uh = 65535','unk84.uh = 255'),signed_mod=b.replace('(u32)func_150ADA20() % 50U','func_150ADA20() % 50'),wrong_mod=b.replace('% 50U','% 49U'),wrong_bias=b.replace('+ 50;','+ 49;'),
      missing_component=b.replace('    func_150615DC(object);\n',''),wrong_tail=b.replace('+ 0x196) = 10','+ 0x196) = 9'),missing_last=b.replace('    *(s16 *)((u8 *)object + 0x19C) = 0;',''),
      late_clear=b.replace('    while ((u32)cursor < (u32)end) {\n        *cursor++ = 0;\n    }\n','').replace('    func_150615DC(object);','    func_150615DC(object);\n    while ((u32)cursor < (u32)end) { *cursor++ = 0; }'))
