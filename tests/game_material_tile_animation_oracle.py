"""Independent material/animation contract with explicit binary32 rounding."""
from dataclasses import dataclass
import itertools,math,struct
from tools.experiments import game_material_tile_animation_candidates as candidate
from tools.experiments import game_material_tile_animation_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
MATERIAL,ACTOR,ANIMATION,HOLDER,COMMANDS=0x30000,0x40000,0x50000,0x60000,0x70000
u32=lambda n:n&0xFFFFFFFF
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]
floating=lambda b:struct.unpack('>f',struct.pack('>I',b))[0]
round32=lambda f:floating(bits(f))

@dataclass(frozen=True)
class Case:
    time:int=0x41F00000
    scale:int=0x3D70F0F1
    kind:int=13
    animation:int=ANIMATION
    material:int=MATERIAL
    actor:int=ACTOR
    index:int=3
    old:int=0xF2ABC123
    primary:int=0x12340548
    alternate:int=0x87650547
    phase:int=0

def symbols():return {'D_80090298':0x80090298,'D_800A0B10':0x800A0B10}

def fixture(c=Case(),s=None):
    s=symbols()if s is None else s
    m={STACK+i:(i*17+165)&255 for i in range(-64,128)}
    for p,n in((c.material,0x40),(c.actor,0x300),(ANIMATION,32),(HOLDER,4),(COMMANDS,(c.index+2)*8)):
        m.update({p+i:(i*29+123)&255 for i in range(n)})
    put(m,c.actor+0x2D0,c.animation);put(m,c.actor+0x84,c.kind,2)
    if c.animation:put(m,c.animation+8,c.time)
    put(m,c.material+0x24,HOLDER);put(m,HOLDER,COMMANDS)
    for i in range(c.index+2):put(m,COMMANDS+i*8,0xE7000000|(i<<12))
    put(m,COMMANDS+c.index*8,c.old)
    put(m,s['D_80090298']+24,c.primary);put(m,s['D_80090298']+28,c.alternate);put(m,s['D_800A0B10'],c.scale)
    return m

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);animation=read(m,c.actor+0x2D0)
    if not animation:return m,0
    put(m,c.material+0x18,read(m,s['D_80090298']+24),2)
    if read(m,c.actor+0x84,2)!=13:return m,0
    time=floating(read(m,animation+8))
    if not(23.0<=time<=40.0):return m,0
    put(m,c.material+0x18,read(m,s['D_80090298']+28),2)
    fraction=round32(floating(read(m,animation+8))-23.0)
    fraction=round32(fraction*floating(read(m,s['D_800A0B10'])))
    commands=read(m,read(m,c.material+0x24));i=0
    while read(m,commands+8*i,1)!=0xF2:i+=1
    p=commands+8*i;previous=(read(m,p)>>12)&0xFFF
    offset=math.trunc(round32(round32(70.0*fraction)+2.0))
    coordinate=offset+previous if offset<0 else offset
    put(m,p,0xF2000002|((coordinate&0xFFF)<<12));return m,0

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.material,c.actor)if arguments is None else arguments)
    def record_call(self,target):
        if target!=source.ENTRY:raise AssertionError(('Unbounded material callback',hex(target)))
        a=tuple(map(u32,self.arguments(2)));self.calls.append((target,a));self.events.append(('CALL',target,a))
    def hook(self,target):raise AssertionError(('Unexpected material helper',hex(target)))

def bound(obj,s):
    raw,bindings=source.function_blob(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in bindings.items():
        if len(rows)!=1:raise ValueError('Material callback relocation pair changed')
        kind,name=rows[0];value=s[name]
        if kind=='R_MIPS_HI16':part=(value+0x8000)>>16&65535
        elif kind=='R_MIPS_LO16':part=value&65535
        else:raise ValueError('Material callback relocation kind changed')
        words[at//4]=(words[at//4]&0xFFFF0000)|part
    return words

def cases():
    times=(0,0x41B7FFFF,0x41B80000,0x41B80001,0x41F00000,0x421FFFFF,0x42200000,0x42200001,0x7FC12345,0x7F800000,0xFF800000)
    for time,kind,animation,index,phase in itertools.product(times,(0,13,0x10D,65535),(0,ANIMATION),(0,1,7),(0,8)):
        yield Case(time=time,kind=kind,animation=animation,index=index,phase=phase)
    for time,scale,index,old in itertools.product((23.,24.,31.5,40.),(0.,-0.5,0.05882352963,2.),(0,4),(0xF2000002,0xF2FFFFFF)):
        yield Case(time=bits(time),scale=bits(scale),index=index,old=old)

def controls():
    b=candidate.SELECTED
    return dict(kind=b.replace('== 13','== 12'),lower=b.replace('>= 23.0f','> 23.0f'),upper=b.replace('<= 40.0f','< 40.0f'),
        first_material=b.replace('D_80090298[6]','D_80090298[5]'),alternate=b.replace('D_80090298[7]','D_80090298[6]'),
        stride=b.replace('commands += index;','commands += index + 1;'),scale=b.replace('70.0f * fraction','69.0f * fraction'),
        negative=b.replace('if (offset < 0)','if (offset > 0)'),mask=b.replace('coordinate & 0xFFF','coordinate & 0x7FF'),
        return_value=b.replace('return 0;','return 1;'))
