"""Independent callback contract and deliberate private-home mismatch witnesses."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_white_text_crossfade_candidates as source
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
OWNER,PAYLOAD,MARK=0x30000,0x50000,0x60000
COLOR,TEXT=0x1504332C,0x15042D94

@dataclass(frozen=True)
class Case:
    count:int=0
    flags:int=0
    ticks:int=1
    index:int=0
    mutation:int=0
    phase:int=0
    alias:int=0

def symbols():return dict(D_800BE9E4=0x800BE9E4,func_1504332C=COLOR,func_15042D94=TEXT)

def fixture(c=Case(),s=None):
    s=symbols() if s is None else s;home=STACK+c.phase
    assert not home-512<=PAYLOAD<home+512
    m={home+i:(i*17+165)&255 for i in range(-512,512)}
    m.update({OWNER+i:(i*13+89)&255 for i in range(128)});m[PAYLOAD]=c.count&255
    put(m,OWNER+0x48,PAYLOAD);m[OWNER+0x30]=c.flags&255;m[OWNER+0x3D]=c.index&255
    # Sparse guest indices are deliberate; native qualification uses 0/1 only.
    for i in range(258):put(m,OWNER+0x40+4*i,0x90000+4*i)
    put(m,OWNER+0x48,PAYLOAD);m[OWNER+0x30]=c.flags&255;m[OWNER+0x3D]=c.index&255
    put(m,s['D_800BE9E4'],c.ticks);put(m,MARK,0)
    return m

def effect(m,c,n):
    put(m,MARK,n+1)
    if c.mutation&1:m[OWNER+0x3D]^=1
    if c.mutation&2:
        put(m,OWNER+0x40,0xB0000+n*16);put(m,OWNER+0x44,0xB0004+n*16)
    if c.mutation&4:m[PAYLOAD]^=0xA5

def reference(initial,c=Case(),s=None):
    s=symbols() if s is None else s;m=dict(initial);p=read(m,OWNER+0x48)
    if m[OWNER+0x30]&1:m[p]=20
    value=m[p] if m[p]<128 else m[p]-256
    alpha=(value*12)%256 if value>0 else 0;inverse=255-alpha
    if value>0:m[p]=(value-read(m,s['D_800BE9E4']))%256
    calls=[]
    def call(t,a):
        n=len(calls);calls.append((t,tuple(v&0xFFFFFFFF for v in a)));effect(m,c,n)
    if inverse:
        call(s['func_1504332C'],(255,255,255,inverse))
        call(s['func_15042D94'],(20,20,128,read(m,OWNER+0x40+4*m[OWNER+0x3D])))
    if alpha:
        text=OWNER+0x28
        call(s['func_1504332C'],(255,255,255,alpha))
        call(s['func_15042D94'],(20,20,128,read(m,text+0x18+4*(m[text+0x15]^1))))
    return m,calls,1

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.c=c;self.s=symbols() if s is None else s
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(OWNER,) if arguments is None else arguments)
        self.before_f=self.f[:]
    def record_call(self,t):
        assert t in(self.s['func_1504332C'],self.s['func_15042D94'],source.ENTRY),hex(t)
        a=tuple(self.arguments(1 if t==source.ENTRY else 4));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t in(self.s['func_1504332C'],self.s['func_15042D94'])
        effect(self.memory,self.c,len([x for x in self.calls if x[0]!=source.ENTRY])-1)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def public(m,c):return {a:b for a,b in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+512}

def payload(obj):
    t,fs,rs=parse_object(obj);f=fs[source.FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:v for p,v in rs.items()if a<=p<a+n}

def bound(obj,s=None):return bound_blob(*payload(obj),symbols() if s is None else s)

def cases():
    ticks=(0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
    for count,flags,index,mutation,phase in itertools.product(range(256),(0,1),(0,1),(0,7),(0,8)):
        yield Case(count,flags,ticks[count%6],index,mutation,phase)
    for count,flags,tick,index,mutation in itertools.product((0,1,20,64,127,128,255),(0,2,255),ticks,(0,1),(0,7)):
        yield Case(count,flags,tick,index,mutation)

def controls():
    b=source.SELECTED
    return dict(unsigned_count=b.replace('s8 *count','u8 *count').replace('(s8 *)','(u8 *)'),
        missing_reset=b.replace('*count = 20;','*count = *count;'),
        wrong_ticks=b.replace('(u32)*count - (u32)D_800BE9E4','(u32)*count + (u32)D_800BE9E4'),
        wrong_scale=b.replace('*count * 12','*count * 13'),
        wrong_inverse=b.replace('255 - opacity','255 + opacity'),
        same_buffer=b.replace('secondText->index ^ 1','secondText->index'),
        false_return=b.replace('return 1;','return 0;'))
