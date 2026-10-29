"""Signed menu records and bounded original callback windows; no gameplay claim."""
from dataclasses import dataclass
from tools.experiments import game_menu_scene_choice_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode
import struct
STATE,OTHER,MARK,INPUT,CALLBACK=0x30000,0x31000,0x40000,0x50000,0x800E0A88
u32=lambda n:n&0xFFFFFFFF
signed8=lambda n:((n&255)^128)-128
signed16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    index:int=2
    choice:int=3
    mode:int=0
    scene:int=-32768
    sequence:int=-128
    alternate:int=127
    mutation:int=0
    phase:int=0
    alias:int=0

def symbols():
    return dict(D_8008FDD4=0x8008FDD4,D_800AB692=0x800AB692,D_800E0C00=0x800E0C00,
        D_800AB7A4=0x800AB7A4,D_8008FD80=0x8008FD80,D_800E0B94=0x800E0B94,
        D_8008FD8C=0x8008FD8C,D_8008FD90=0x8008FD90,
        func_1501D348=source.LAUNCH,func_151E2834=source.FALLBACK)
FLAG_NAMES=('D_8008FD80','D_800E0B94','D_8008FD8C','D_8008FD90')
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for a,n in((STATE,256),(OTHER,256),(MARK,16),(INPUT,64),(CALLBACK,32),(0x8008FD74,1)):
        for i in range(n):m[a+i]=165
    for name,a in s.items():
        if name.startswith('D_'):
            for i in range(4):m[a+i]=165
    for i in range(-1300,1301):m[u32(s['D_800AB692']+i)]=165
    for i in range(256):
        a=s['D_800AB7A4']+4*i;put(m,a,(c.scene+i)&65535,2);m[a+2]=(c.sequence+i)&255;m[a+3]=(c.alternate-i)&255
    a=s['D_800AB7A4']+4*(c.choice&255);put(m,a,c.scene&65535,2);m[a+2]=c.sequence&255;m[a+3]=c.alternate&255
    # Aliased state byte can be a selected record byte or one of the post-call flags.
    state=(STATE,s['D_800AB7A4']+2-0x42,s['D_8008FD90']-0x42)[c.alias]
    put(m,s['D_8008FDD4'],state);m[state+0x42]=c.index&255
    m[u32(s['D_800AB692']+signed8(c.index)*10)]=c.choice&255;m[s['D_800E0C00']]=c.mode&255
    put(m,CALLBACK,source.FALLBACK)
    return m

def effect(m,c,s):
    put(m,MARK,0xABCDEF01)
    if c.mutation:
        ptr=read(m,s['D_8008FDD4']);m[ptr+0x42]=0xFF;put(m,s['D_8008FDD4'],OTHER)
        m[s['D_800AB692']]=0xFF;m[s['D_800E0C00']]=0x80
        put(m,s['D_800AB7A4'],0xFFFFFFFF)
        for n in FLAG_NAMES:m[s[n]]=0xCC

def observe(m,s):return tuple(m[s[n]]for n in FLAG_NAMES)
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);idx=signed8(m[read(m,s['D_8008FDD4'])+0x42]);choice=signed8(m[u32(s['D_800AB692']+10*idx)])
    if choice<0:target=s['func_151E2834'];args=()
    else:
        a=s['D_800AB7A4']+4*choice;target=s['func_1501D348'];args=(u32(signed16(read(m,a,2))),u32(signed8(m[a+(3 if m[s['D_800E0C00']]else 2)])),0,0,0)
    observation=(target,observe(m,s));effect(m,c,s)
    if choice>=0:
        for n,v in zip(FLAG_NAMES,(1,5,1,1)):m[s[n]]=v
    return m,[(target,args)],[observation]

class MenuSceneOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
        self.case=c;self.syms=symbols()if s is None else s
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(0x12345678,),connected=connected)
        self.trace=[];self.observations=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,a,n):
        v=super().get(a,n)
        if self.own_instruction:self.trace.append(('R',a,n,v))
        return v
    def put(self,a,v,n):
        super().put(a,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
    def execute(self,w):
        if w>>26==32:
            self.own_instruction=True
            try:self.r[w>>16&31]=u32(signed8(self.get(u32(self.r[w>>21&31]+signed16(w)),1)))
            finally:self.own_instruction=False
            self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        counts={source.ENTRY:0,self.syms['func_1501D348']:5,self.syms['func_151E2834']:0}
        assert t in counts,('Unbounded menu scene provider',hex(t));args=tuple(map(u32,self.arguments(counts[t])))
        self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append((t,observe(self.memory,self.syms)))
    def hook(self,t):
        assert t in(self.syms['func_1501D348'],self.syms['func_151E2834'])
        effect(self.memory,self.case,self.syms)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

WINDOWS=((0x151E15D4,20,0x151E1624),(0x151E1E60,21,0x151E1EB4),(0x151E5014,4,0x151E5024))
def window_machine(rom,words,c=Case(),window=0,selector=0,buttons=0,initial=None):
    entry,n,end=WINDOWS[window];m=fixture(c)if initial is None else dict(initial)
    if window==1:put(m,INPUT+0x20,buttons,2)
    body=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0)
    connected={end:0}
    if window==2:connected.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words))
    machine=MenuSceneOracle(body,m,c,entry=entry,connected=connected);machine.r[17]=u32(selector);machine.r[24]=INPUT;machine.before=machine.r[:];machine.code=WindowCode(machine.code,machine);machine.code.ends=(end,)
    expected=dict(m)
    if window==0:
        i=signed8(expected[read(expected,0x8008FDD4)+0x42]);ch=signed8(expected[0x800AB692+10*i]);put(expected,CALLBACK,source.FALLBACK if u32(selector)==u32(ch)else source.ENTRY)
    elif window==1:
        if buttons&0x10:expected[0x800E0B94]=7;put(expected,CALLBACK,source.ENTRY);expected[0x8008FD74]=8;put(expected,STACK+c.phase+0x74,0x500)
        elif buttons&0x20:expected[0x800E0A96]=4
    return machine,expected
