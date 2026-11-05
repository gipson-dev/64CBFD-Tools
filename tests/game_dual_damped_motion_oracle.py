"""Independent rounded motion reference and original registered caller support."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_dual_damped_motion_match as match
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_effect_owner_ray as ray
ACTOR,STEP,TABLE=0x30000,0x800BE9A4,0x80089CB8
WRITTEN=tuple(range(0x34,0x4C,4))+tuple(range(0x140,0x158,4))
INPUTS=WRITTEN+(0x158,0x15C,0x160)
VALUES=((0,0x80000000,0,0x80000000,0,0x80000000),tuple(map(bits,(1.25,-2.5,3.75,-4.5,5.25,-6.75))),
    (1,0x80000001,0x00800000,3,0x80000003,0x00800001),tuple(map(bits,(1e12,-1e12,.25,-.5,1e12,-1e12))),
    tuple(map(bits,(-.125,.375,-.625,.75,-.875,1.125))),tuple(map(bits,(-19,23,-29,31,-37,41))))
POINTS=(tuple(map(bits,(1,2,3,11,-13,17))),tuple(map(bits,(1e-25,-1e-25,1e12,-1e12,1e12,-1e-25))))
@dataclass(frozen=True)
class Case:
    step:int=0x3F000000
    damping:int=0x3F000000
    end_damping:int=0x3E800000
    acceleration:int=0xBE800000
    pattern:int=1
    points:int=0
    layout:int=-1
def owner(c,step=STEP):return ACTOR if c.layout<0 else step-c.layout
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def fixture(c=Case(),step=STEP):
    actor=owner(c,step);m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    m.update({actor+i:(i*13+89)&255 for i in range(0x164)})
    for at,v in zip(WRITTEN,POINTS[c.points]+VALUES[c.pattern]):put(m,actor+at,v)
    for at,v in((0x158,c.acceleration),(0x15C,c.damping),(0x160,c.end_damping)):put(m,actor+at,v)
    put(m,step,c.step);return m
def reference(initial,c=Case(),step=STEP):
    m=dict(initial);actor=owner(c,step)
    damping,acceleration,end_damping=(read(m,actor+at)for at in(0x15C,0x158,0x160))
    # Round each multiply and add independently; never fuse or reassociate.
    for base,factor in((0x140,damping),(0x14C,end_damping)):
        put(m,actor+base,mul(read(m,actor+base),factor))
        put(m,actor+base+4,add(read(m,actor+base+4),mul(acceleration,read(m,step))))
        put(m,actor+base+8,mul(read(m,actor+base+8),factor))
    for at,velocity in zip(range(0x34,0x4C,4),range(0x140,0x158,4)):
        put(m,actor+at,add(read(m,actor+at),mul(read(m,actor+velocity),read(m,step))))
    return m
def corpus():
    for args in itertools.product((0,0x80000000,1,bits(.5),bits(-1),bits(2.5)),map(bits,(0,-0.0,.5,-.75,1.25)),
        map(bits,(-0.0,.25,-1.25)),map(bits,(0,-9.8,.25)),range(6),range(2)):yield Case(*args)
class Oracle(ray.RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=match.ENTRY,step=STEP,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=(owner(c,step),),connected=connected)
    def record_call(self,t):
        if t!=match.ENTRY:raise AssertionError(('Unbounded dual damped motion provider',hex(t)))
        a=self.arguments(1);self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):raise AssertionError(('Unexpected motion provider',hex(t)))
