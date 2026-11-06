"""Independent byte reference for quad banks, optional state and factory ABI."""
from dataclasses import dataclass, replace
import itertools
from tools.experiments import game_double_bank_record_constructor_candidates as source
from tools.tests.game_table_payload_spawn_oracle import Oracle as InstructionOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read

RESULT, OWNER, OTHER = 0x60000, 0x70000, 0x78000
FACTORY, CORE, INIT = 0x15167A68, 0x10003C6C, 0x15168A4C
SYMS = dict(func_15167A68=FACTORY)
PATTERNS = (0, 1, 128, 255, 0x80000000, 0xFFFFFFFF)
HALVES = tuple(0x90 + bank*64 + vertex*16 + field for bank in range(2) for vertex in range(4) for field in (6, 8, 10))

@dataclass(frozen=True)
class Case:
    kind: int = 1
    owner: int = OWNER
    mode: int = 2
    flags: int = 1
    variant: int = 1
    outcome: int = 1
    phase: int = 0
    mutation: int = 0
    record: int = RESULT
    factory: bool = False

def public(m): return {a:v for a,v in m.items() if not STACK-1024 <= a < STACK+1024}

def fixture(c=Case()):
    m = {STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    for p,n in ((c.record-16,0x160),(OWNER,0x400),(OTHER,0x400)):
        m.update({p+i:(i*13+89)&255 for i in range(n)})
    put(m,STACK+c.phase+16,c.variant)
    return m

def effect(m,c,home):
    if c.mutation&1:
        for i in range(0x13A):m[c.record+i]=(i*7+0x31)&255
    if c.mutation&2:
        for off,v in ((0x30,0x812345FF),(0x34,OTHER),(0x38,0xABCDEF80),(0x40,0xDEAD007F)):put(m,home+off,v)
    if c.mutation&4:put(m,home+0x20,0 if c.flags&1 else 0x80000000)
    if c.mutation&8:put(m,OWNER+0x10,0x33445566)

def initializer(m,record):
    put(m,record+0x20,0xAABBCCDD)
    m[record+0x44]=0xE7

def reference(initial,c=Case(),s=SYMS,home=None,ra=0xDEAD0000):
    m=dict(initial);home=STACK+c.phase-0x30 if home is None else home
    for off,value in ((0x1C,ra),(0x30,c.kind),(0x34,c.owner),(0x38,c.mode)):put(m,home+off,value)
    extra=c.flags&1;size=0x13A if extra else 0x128
    put(m,home+0x28,size);put(m,home+0x14,1);put(m,home+0x10,255);put(m,home+0x20,extra)
    calls=[(s['func_15167A68'],(0x4B,0,size,1,255,1))]
    if c.factory:calls.append((CORE,(size,1,1,0,1)))
    effect(m,c,home)
    for i in range(4):put(m,home+4*i,0xB5000000+i)
    result=c.record if c.outcome else 0
    if c.factory and result:
        m[result+1]=0;calls.append((INIT,(result,0x4B)));initializer(m,result);m[result+12]=255
    extra=read(m,home+0x20)
    if result:
        for bank in range(2):
            for vertex,(u,v) in enumerate(((0x800,0),(0,0),(0,0x800),(0x800,0x800))):
                p=result+0x90+bank*64+vertex*16
                put(m,p+6,0,2);put(m,p+8,u,2);put(m,p+10,v,2)
        m[result+0x120]=read(m,home+0x30)&255
        put(m,result+0x110,read(m,home+0x34))
        m[result+0x121]=read(m,home+0x38)&255
        m[result+0x124]=read(m,home+0x40)&255
        if extra:
            for i in range(9):put(m,result+0x128+2*i,0x7FFF,2)
    return m,calls,result

class Oracle(InstructionOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None):
        self.c,self.s=c,s;self.home=STACK+c.phase-0x30
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,
            arguments=(c.kind,c.owner,c.mode,c.flags,c.variant),connected=connected)
        self.before_f=self.f[:]
    def record_call(self,t):
        counts={source.ENTRY:5,self.s['func_15167A68']:6,CORE:5,INIT:2}
        if t not in counts:raise AssertionError(('Unbounded quad constructor provider',hex(t)))
        a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        a=self.calls[-1][1];value=0xDEADBEEF
        if t in (self.s['func_15167A68'],CORE):
            effect(self.memory,self.c,self.home);value=self.c.record if self.c.outcome else 0
        elif t==INIT:
            assert a==(self.c.record,0x4B);initializer(self.memory,a[0])
        else:raise AssertionError(('Unknown quad constructor provider',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value&0xFFFFFFFF

def cases():
    for kind,mode,flags,variant,outcome,phase in itertools.product(PATTERNS,PATTERNS,(0,1,2,0xFFFFFFFF),PATTERNS,(0,1),(0,8)):
        yield Case(kind=kind,mode=mode,flags=flags,variant=variant,outcome=outcome,phase=phase)
    for field,byte,flags in itertools.product(('kind','mode','variant'),range(256),(0,1)):
        yield replace(Case(flags=flags),**{field:0xA5A50000|byte})
    for flags,mutation,outcome,phase in itertools.product((0,1,2,0xFFFFFFFF),(0,1,2,4,8,15),(0,1),(0,8)):
        yield Case(flags=flags,mutation=mutation,outcome=outcome,phase=phase)
    for owner,flags,outcome in itertools.product((0,4,OWNER,RESULT+4,0x80000000,0xFFFFFFFF),(0,1),(0,1)):
        yield Case(owner=owner,flags=flags,outcome=outcome)

def controls():
    b=source.SELECTED
    changes={
        'all_flag_bits':('if (flags & 1)','if (flags)'),
        'short_base_size':('bytes = 0x128','bytes = 0x124'),
        'short_optional_size':('bytes = 0x13A','bytes = 0x138'),
        'wrong_factory_kind':('func_15167A68(0x4B','func_15167A68(0x4A'),
        'one_bank':('i < 2','i < 1'),
        'wrong_bank_stride':('i * 0x40','i * 0x30'),
        'wrong_texture_coordinate':('= 0x800','= 0x400'),
        'wrong_owner_field':('record + 0x110','record + 0x114'),
        'wrong_mode_byte':('record[0x121] = mode','record[0x121] = mode >> 8'),
        'wrong_variant_byte':('record[0x124] = variant','record[0x124] = variant >> 8'),
        'short_tail':('i < 9','i < 8'),
        'zero_tail':('= 0x7FFF','= 0'),
        'clear_retained_byte':('record[0x121] = mode;','record[0x121] = mode;\n        record[0x122] = 0;')}
    result={n:b.replace(a,z) for n,(a,z) in changes.items()}
    if any(v==b for v in result.values()):raise ValueError('Ineffective quad constructor control')
    return result
