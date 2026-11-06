"""Rounded dual-point reference, including the real saved-weight alias lifetime."""
from dataclasses import dataclass
import itertools,math
from tools.experiments import game_dual_point_weighted_motion_candidates as source
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_point_transform_match import put,read
ACTOR,STEP,TABLE=0x30000,0x800BE9A4,0x80089CB8
WRITTEN=tuple(range(0x34,0x4C,4))+tuple(range(0x130,0x13C,4))
INPUTS=WRITTEN+(0x13C,0x140,0x54)
VALUES=((0,0x80000000,0),tuple(map(bits,(1.25,-2.5,3.75))),tuple(map(bits,(-19,23,-29))),
    (1,0x80000001,0x00800000),tuple(map(bits,(1e12,-1e12,.25))),tuple(map(bits,(-.125,.375,-.625))),
    (0x7F800000,0xFF800000,0),(0x7FC12345,0x7F800001,0xFFC56789))
POINTS=(tuple(map(bits,(1,2,3,11,-13,17))),tuple(map(bits,(1e-25,-1e-25,1e12,-1e12,1e12,-1e-25))))
@dataclass(frozen=True)
class Case:
    step:int=0x3F000000
    damping:int=0x3F000000
    acceleration:int=0xBE800000
    blend:int=0x3E800000
    pattern:int=1
    points:int=0
    layout:int=-1
    phase:int=0
    at:int=0
def owner(c,step=STEP):return c.at if c.at else ACTOR if c.layout<0 else step-c.layout
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def fixture(c=Case(),step=STEP):
    actor=owner(c,step);m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    m.update({actor+i:(i*13+89)&255 for i in range(0x144)})
    for at,v in zip(WRITTEN,POINTS[c.points]+VALUES[c.pattern]):put(m,actor+at,v)
    for at,v in((0x13C,c.acceleration),(0x140,c.damping),(0x54,c.blend)):put(m,actor+at,v)
    put(m,step,c.step);return m
def reference(initial,c=Case(),step=STEP,home=None):
    m=dict(initial);a=owner(c,step);home=STACK+c.phase-24 if home is None else home
    damping,x,accel=(read(m,a+n)for n in(0x140,0x130,0x13C));put(m,a+0x130,mul(x,damping))
    early=read(m,step);y=read(m,a+0x134);z=read(m,a+0x138)
    new_y=add(y,mul(accel,early));new_z=mul(z,damping)
    vx=read(m,a+0x130);put(m,a+0x134,new_y);vy=read(m,a+0x134);put(m,a+0x138,new_z)
    late=read(m,step);vz=read(m,a+0x138);changes=[mul(v,late)for v in(vx,vy,vz)]
    for base in(0x34,0x40):
        for i,v in enumerate(changes):put(m,a+base+4*i,add(read(m,a+base+4*i),v))
    weight=read(m,a+0x54);first_x=read(m,a+0x34);put(m,home+4,weight)
    anchors=(first_x,read(m,a+0x38),read(m,a+0x3C))
    for i,v in enumerate(anchors):
        at=a+0x40+4*i;put(m,at,add(v,mul(sub(read(m,at),v),read(m,home+4))))
    return m
def equivalent(actual,expected,c=Case(),step=STEP,home=None):
    a,b=dict(actual),dict(expected);home=STACK+c.phase-24 if home is None else home
    for p in{owner(c,step)+n for n in WRITTEN}|{home+4}:
        if math.isnan(floating(read(a,p)))and math.isnan(floating(read(b,p))):put(a,p,0x7FC00000);put(b,p,0x7FC00000)
    return a==b
def cases():
    for args in itertools.product((0,0x80000000,1,bits(.5),bits(-1),bits(2.5)),map(bits,(0,-0.0,.5,-.75,1.25)),map(bits,(0,-9.8,.25)),map(bits,(-1,-0.0,0,.25,.5,1,1.5)),range(8),range(2)):yield Case(*args)
class Oracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,step=STEP,connected=None):
        self.case=c;self.step=step
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(owner(c,step),),connected=connected)
        self.before_f=self.f[:]
    def record_call(self,t):
        if t not in(source.ENTRY,0x1516972C):raise AssertionError(('Unbounded weighted-motion provider',hex(t)))
        a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        if t!=0x1516972C:raise AssertionError(('Unowned weighted-motion provider',hex(t)))
        # Only the false-return caller control reaches this opaque cleanup.
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.r[2]=0

def controls():
    b=source.SELECTED
    rows=dict(wrong_return=('return 1;','return 0;'),missing_x_damping=('    *(f32 *)(owner + 0x130) *= *(f32 *)(owner + 0x140);\n',''),
        missing_z_damping=('    *(f32 *)(owner + 0x138) *= *(f32 *)(owner + 0x140);\n',''),
        inverted_acceleration=('*(f32 *)(owner + 0x134) +=','*(f32 *)(owner + 0x134) -='),
        wrong_end_z_step=('record[0x48 / 4] += zComponent','record[0x48 / 4] += yComponent'),
        wrong_weight_field=('weight = record[0x54 / 4]','weight = record[0x140 / 4]'),
        reversed_blend=('record[0x40 / 4] - firstX','firstX - record[0x40 / 4]'),
        wrong_y_axis=('record[0x44 / 4] - yComponent','record[0x48 / 4] - yComponent'))
    result={n:b.replace(a,z,1)for n,(a,z)in rows.items()}
    early=b.replace('    f32 firstX;','    f32 firstX;\n    f32 earlyStep = D_800BE9A4;').replace(' * D_800BE9A4',' * earlyStep')
    result['early_timestep']=early
    if any(v==b for v in result.values()):raise ValueError('Ineffective weighted-motion control')
    return result
