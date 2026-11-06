"""Constructor byte semantics, private padding, aliases and original effect factory."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_oriented_effect_parameters_match as source
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_oriented_effect_factory_oracle as factory
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
OWNER,MARK=0x30000,factory.MARK
HELPER=0x15152F70
PADDING=(0x3A,0x3B,0x56,0x57)

@dataclass(frozen=True)
class Case:
    mode:int=0
    phase:int=0
    seed:int=0
    owner:int=OWNER
    mutation:int=0

def symbols():return dict(D_800A0C24=0x800A0C24,D_800A0C28=0x800A0C28,D_800A0C2C=0x800A0C2C,D_800A0C30=0x800A0C30,func_15152F70=HELPER)

def providers():return {n:int(n.split('_')[1],16) for n in('func_150ADA20','func_150ADA68','func_151423D8','func_15147DA0')}

def values(seed):
    patterns=(0,0x80000000,0x3F800000,0xBF800000,1,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC54321)
    return tuple(patterns[(seed+i*3)%len(patterns)] for i in range(4))

def fixture(c=Case(),s=None):
    s=symbols() if s is None else s;home=STACK+c.phase
    m={home+i:0xCD if i < -112 else (i*17+c.seed*13+165)&255 for i in range(-4096,1024)}
    m.update({OWNER+i:(i*29+c.mode)&255 for i in range(128)})
    m.update({MARK+i:(i*7+90)&255 for i in range(1024)})
    for n,v in zip(('D_800A0C24','D_800A0C28','D_800A0C2C','D_800A0C30'),values(c.seed)):put(m,s[n],v)
    m[c.owner+12]=c.mode&255
    return m

def packet(initial,home,s,ra):
    """Independent field map with the observed global read/store alias boundaries."""
    m=dict(initial);sp=home-112;p=sp+24;put(m,sp+20,ra)
    x,y,z=(read(m,s[n]) for n in('D_800A0C24','D_800A0C28','D_800A0C2C'))
    put(m,p,x);field14=read(m,s['D_800A0C30'])
    for off,v in((0x24,1),(0x26,2),(0x28,-75),(0x2C,-38),(0x2A,22),(0x2E,35),(0x30,3),(0x32,2),(0x34,41),(0x36,0)):put(m,p+off,v,2)
    for off in(0x0C,0x10):put(m,p+off,0x40000000)
    m[p+0x38]=10;m[p+0x39]=40;put(m,p+0x3C,1)
    for off in(0x40,0x44,0x48,0x4C,0x50):put(m,p+off,0)
    m[p+0x54]=m[p+0x55]=255
    for off,v in((4,y),(8,z),(0x1C,0x40E00000),(0x20,0x40A00000),(0x14,field14),(0x18,0)):put(m,p+off,v)
    return m,p

def effect(m,c,s,p):
    put(m,MARK,0xCA110000|c.mutation)
    if c.mutation&1:m[c.owner+12]^=255;put(m,s['D_800A0C24'],0x12345678)
    if c.mutation&2:put(m,p,0x87654321);m[p+0x55]=19

def reference(initial,c=Case(),s=None,ra=0):
    s=symbols() if s is None else s;m,p=packet(initial,STACK+c.phase,s,ra)
    a=(p,m[c.owner+12]);observation=(bytes(m[p+i] for i in range(88)),a)
    effect(m,c,s,p)
    for i in range(4):put(m,STACK+c.phase-112+4*i,0xB5000000+i)
    return m,[(s['func_15152F70'],a)],observation

class Oracle(factory.Machine):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.case=c;self.s=symbols() if s is None else s;self.home=STACK+c.phase-112;self.target=entry;self.providers=providers();self.raw=False
        self.rng_i=self.rng_f=self.trig_i=self.submits=0;self.payloads=[];self.packets=[];self.target_calls=[]
        factory.FactoryOracle.__init__(self,words,memory,c,entry=entry,s={},connected=connected,arguments=(c.owner,) if arguments is None else arguments)
        self.before_f=self.f[:]
    def record_call(self,target):
        if target==source.ENTRY:
            a=tuple(self.arguments(1));self.target_calls.append(a)
        elif target==self.s['func_15152F70']:
            a=tuple(self.arguments(2));self.packets.append((bytes(self.memory[a[0]+i] for i in range(88)),a))
        else:return factory.Machine.record_call(self,target)
        self.calls.append((target,a));self.events.append(('CALL',target,a))
    def hook(self,target):
        if target!=self.s['func_15152F70']:return factory.Machine.hook(self,target)
        effect(self.memory,self.case,self.s,self.calls[-1][1][0])
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def bound(obj,s=None):return bound_blob(*source.function_blob(obj),symbols() if s is None else s)

def cases():
    for mode,phase,seed,mutation in itertools.product(range(256),(0,8),range(2),(0,3)):yield Case(mode,phase,seed,mutation=mutation)
    for seed in range(10):yield Case(seed*23,seed%2*8,seed)

def controls():
    b=source.candidate.SELECTED
    return dict(wrong_mode=b.replace('((u8 *)owner)[0x0C]','((u8 *)owner)[0x0D]'),wrong_count=b.replace('input.countRange = 2','input.countRange = 1'),wrong_angle=b.replace('input.firstAngleBase = -75','input.firstAngleBase = 75'),wrong_speed=b.replace('input.speedBase = 7.0f','input.speedBase = 5.0f'),wrong_global=b.replace('input.field14Base = D_800A0C30','input.field14Base = D_800A0C2C'),wrong_flags=b.replace('input.fixed55 = 255','input.fixed55 = 127'),cleared_padding=b.replace('OrientedEffectInput input;','OrientedEffectInput input;\n    input.private3A[0] = input.private3A[1] = input.privateTail56[0] = input.privateTail56[1] = 0;'))
