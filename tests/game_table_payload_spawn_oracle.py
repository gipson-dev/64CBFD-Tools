"""Byte-exact table snapshot, retained request padding and live guest copy order."""
from dataclasses import dataclass
import math
from tools.experiments import game_table_payload_spawn_candidates as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_point_transform_match import put,read
ACTOR,OUTPUT,TABLE,CREATE,COPY,REGISTRY=0x30000,0x40000,0x800A636C,0x151A8B20,0x10022EC0,0x8008F984
SYMS=dict(D_800A636C=TABLE,func_151A8B20=CREATE,memcpy=COPY)
DEFINED=(0,*range(4,39))
PATTERNS=(0,0x80000000,1,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,0xFFFFFFFF)

@dataclass(frozen=True)
class Case:
    gate:int=0
    allocated:bool=True
    mode:int=0
    pattern:int=0
    phase:int=0
    actor:int=ACTOR
    alias:int=0
    unused:int=0xFEDCBA98

def fixture(c=Case(),s=SYMS):
    m={STACK+i:(i*17+c.pattern*29+165)&255 for i in range(-1024,1024)}
    for p,n in((c.actor,256),(OUTPUT,256),(s['D_800A636C'],52)):
        m.update({p+i:(i*13+c.pattern*17+89)&255 for i in range(n)})
    for i in range(13):put(m,s['D_800A636C']+4*i,PATTERNS[(i+c.pattern)%len(PATTERNS)])
    m[c.actor+0x1F]=c.gate
    return m

def result(c,s=SYMS,home=None):
    home=STACK+c.phase-136 if home is None else home
    return 0 if not c.allocated else (OUTPUT,c.actor-128,s['D_800A636C']-128,home+0x2C-128,home+0x60-128)[c.alias]

def effect(m,c,s,home):
    if c.mode&1:m[c.actor+0x1F]=255;put(m,c.actor+0x20,0xDEADBEEF)
    if c.mode&2:
        for i in range(52):m[s['D_800A636C']+i]=(i*31+0xA7)&255
    if c.mode&4:put(m,home+0x68,0x12345678);m[home+0x61]=0xED
    if c.mode&8:
        # Guest-only access to the retained local payload, distinct from
        # portable native providers, which receive only the request pointer.
        m[home+0x2C]=0xD1;m[home+0x57]=0xE2

def clobber_homes(m,home):
    for i in range(4):put(m,home+4*i,0xB5000000+i)

def reference(initial,c=Case(),s=SYMS,home=None,ra=0xDEAD0000):
    m=dict(initial);home=STACK+c.phase-136 if home is None else home
    put(m,home+0x1C,ra);put(m,home+136,c.actor);put(m,home+140,c.unused)
    calls=[]
    if m[c.actor+0x1F]>0:return m,calls
    at=s['D_800A636C'];owner=read(m,home+136)
    head=bytes(m[at+i]for i in range(12))
    m[home+0x60]=15;m[home+0x84]=0;m[home+0x85]=255;m[home+0x86]=2
    for off in range(0x70,0x84,4):put(m,home+off,0)
    put(m,home+0x64,owner)
    for i in range(8):m[home+0x68+i]=head[i]
    for i in range(4):m[home+0x2C+i]=head[8+i]
    # Retail copies one word at a time after constructing the request; a
    # table/frame overlap can change later source words during this loop.
    for i in range(10):put(m,home+0x30+4*i,read(m,at+12+4*i))
    put(m,home+0x10,0)
    request=bytes(m[home+0x60+i]for i in range(40))
    calls.append((s['func_151A8B20'],(home+0x60,0xFFFFFFFF,44,255,0),request))
    effect(m,c,s,home);created=result(c,s,home);clobber_homes(m,home)
    if created:
        dst=created+128;src=home+0x2C
        calls.append((s['memcpy'],(dst,src,44),bytes(m[src+i]for i in range(44))))
        for i in range(44):m[dst+i]=m[src+i]
        clobber_homes(m,home)
    return m,calls

class Oracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None,home=None):
        self.c,self.s=c,s;self.home=STACK+c.phase-136 if home is None else home
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.actor,c.unused),connected=connected)
        self.before_f=self.f[:];self.constructor_memory=None;self.constructor_sp=None

    def execute(self,w):
        self.dispatched_word=w
        op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op==17 and rs==16 and w&63==13:
            from tools.tests.game_animation_timeline_oracle import floating
            value=floating(self.f[w>>11&31]);assert math.isfinite(value)and -2147483648<=value<2147483648
            self.f[w>>6&31]=math.trunc(value)&0xFFFFFFFF;return
        if op not in(34,38,42,46):return super().execute(w)
        prior=self.own_instruction;self.own_instruction=True
        try:
            at=(self.r[rs]+(((w&65535)^32768)-32768))&0xFFFFFFFF;base=at&~3;lane=at&3
            if op==34:
                n=4-lane;v=self.get(at,n);self.r[rt]=((v<<(8*lane))|(self.r[rt]&((1<<(8*lane))-1)))&0xFFFFFFFF
            elif op==38:
                n=lane+1;v=self.get(base,n);mask=(~((1<<(8*n))-1))&0xFFFFFFFF;self.r[rt]=(self.r[rt]&mask)|v
            elif op==42:self.put(at,self.r[rt]>>(8*lane),4-lane)
            else:
                n=lane+1;self.put(base,self.r[rt]&((1<<(8*n))-1),n)
            self.r[0]=0
        finally:self.own_instruction=prior

    def record_call(self,t):
        if t==source.ENTRY:
            a=tuple(self.arguments(2));self.calls.append((t,a,None));self.events.append(('CALL',t,a));return
        if t==self.s['func_151A8B20']:
            a=tuple(self.arguments(5));p=a[0];value=bytes(self.memory[p+i]for i in range(40))
            assert a==(self.home+0x60,0xFFFFFFFF,44,255,0),a
            self.constructor_memory=dict(self.memory);self.constructor_sp=self.r[29]
        elif t==self.s['memcpy']:
            a=tuple(self.arguments(3));value=bytes(self.memory[a[1]+i]for i in range(a[2]))
        else:raise AssertionError(('Unbounded table-payload provider',hex(t)))
        self.calls.append((t,a,value));self.events.append(('CALL',t,a))

    def hook(self,t):
        if t==self.s['func_151A8B20']:
            effect(self.memory,self.c,self.s,self.home);value=result(self.c,self.s,self.home)
        else:
            assert t==self.s['memcpy'];a=self.calls[-1][1];value=a[0]
            for i in range(a[2]):self.put(a[0]+i,self.memory[a[1]+i],1)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value

def controls():
    b=source.SELECTED
    changes={
        'signed_gate':('u8 index =','s8 index ='),
        'wrong_kind':('request.kind = 0x0F','request.kind = 0x0E'),
        'wrong_primary':('request.primary = entry->primary','request.primary = entry->secondary'),
        'wrong_mode':('request.mode = -1','request.mode = 0'),
        'wrong_factory_size':('&request, -1, 0x2C','&request, -1, 0x28'),
        'wrong_channel':('0x2C, 0xFF, 0','0x2C, 0x7F, 0'),
        'wrong_fifth':('0x2C, 0xFF, 0','0x2C, 0xFF, 1'),
        'short_copy':('sizeof(payload)','sizeof(payload) - 1'),
        'wrong_destination':('created + 0x80','created + 0x7C')}
    result={n:b.replace(a,z,1)for n,(a,z)in changes.items()}
    if any(v==b for v in result.values()):raise ValueError('Ineffective table-payload control')
    return result
