"""Independent rounded extent updates and the original five-byte setter contract."""
from dataclasses import dataclass
import itertools, math
from tools.experiments import game_dual_extent_approach_candidates as source
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_point_transform_match import put, read

ACTOR, CONSTANT, SETTER, TABLE = 0x30000, 0x800A57A0, 0x1513F680, 0x80089D60
FIELDS = (0x2C, 0x30, 0x118, 0x128)
FACTORS = (0x3F333333, 0x3F733333, 0x3F333333, 0x3F733333)
PAIRS = tuple(tuple(map(bits, p)) for p in ((0, 10), (10, 10), (-10, -10),
    (0, 0), (-0.0, 0), (9.5, 10), (11, 10), (1e-25, 1e-24))) + (
    (1, 0x00800000), (0x7F7FFFFF, 0xFF7FFFFF), (0x7F800000, 0x7F800000),
    (0x7FC12345, bits(10)), (bits(10), 0x7F800001))

@dataclass(frozen=True)
class Case:
    flags: int = 0
    x: int = 0
    y: int = 1
    phase: int = 0
    at: int = ACTOR
    selectors: tuple = (0x80, 0xFE, 0xFF)

def fixture(c=Case(), constants=CONSTANT):
    m = {STACK+i: (i*17+165)&255 for i in range(-1024, 1024)}
    m.update({c.at+i: (i*13+89)&255 for i in range(0x12C)})
    for off, v in zip(FIELDS, (PAIRS[c.x][0], PAIRS[c.y][0], PAIRS[c.x][1], PAIRS[c.y][1])):
        put(m, c.at+off, v)
    for off, v in zip((0x70, 0x72, 0x73), c.selectors):m[c.at+off] = v
    m[c.at+0x71], m[c.at+0x74] = 5, c.flags
    for i, v in enumerate(FACTORS):put(m, constants+4*i, v)
    return m

def reference(initial, c=Case(), constants=CONSTANT, home=None, ra=0xDEAD0000):
    m = dict(initial); a = c.at; complete = True
    home = STACK+c.phase-32 if home is None else home
    put(m, home+0x1C, ra)
    for off, target, mask, index in ((0x2C, 0x118, 2, 0), (0x30, 0x128, 8, 2)):
        if m[a+0x74]&mask:continue
        old, end, factor = (read(m, p) for p in (a+off, a+target, constants+4*index))
        delta = bits(floating(end)-floating(old))
        change = bits(floating(delta)*floating(factor))
        put(m, a+off, bits(floating(old)+floating(change)))
        threshold = bits(floating(read(m, a+target))*floating(read(m, constants+4*(index+1))))
        if floating(threshold)<floating(read(m, a+off)):m[a+0x74] |= mask
        else:complete = False
    calls = []
    if complete:
        args = (a, m[a+0x70], 4, m[a+0x72], m[a+0x73])
        put(m, home+0x10, args[4]); calls.append((SETTER, args))
        for off, v in zip((0x70, 0x71, 0x72, 0x73), args[1:]):m[a+off] = v
    return m, calls

def equivalent(actual, expected, c=Case()):
    a, b = dict(actual), dict(expected)
    for off in (0x2C, 0x30):
        p=c.at+off
        if math.isnan(floating(read(a,p))) and math.isnan(floating(read(b,p))):
            put(a,p,0x7FC00000); put(b,p,0x7FC00000)
    return a==b

def cases():
    for flag, x, y in itertools.product(range(256), range(len(PAIRS)), (0,1,3,11)):
        yield Case(flag,x,y,8*(flag&1))

class Oracle(RayOracle):
    def __init__(self, words, memory, c=Case(), entry=source.ENTRY, connected=None, setter=SETTER):
        self.case, self.setter = c, setter
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.at,),connected=connected)
        self.before_f=self.f[:]

    def record_call(self,t):
        count = 5 if t==self.setter else 1
        if t not in (self.setter,source.ENTRY,0x1516972C):
            raise AssertionError(('Unbounded extent provider',hex(t)))
        args=tuple(self.arguments(count)); self.calls.append((t,args)); self.events.append(('CALL',t,args))

    def hook(self,t):
        if t==self.setter:
            a,*values=self.calls[-1][1]
            for off,v in zip((0x70,0x71,0x72,0x73),values):self.put(a+off,v&255,1)
        elif t!=0x1516972C:raise AssertionError(('Unowned extent provider',hex(t)))
        # The real setter is connected in the caller test. This adversarial
        # bounded alternative verifies that caller-saved registers stay dead.
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]

def controls():
    b=source.SELECTED
    changes = {
        'wrong_return':('return 1;','return 0;'),
        'skip_y_after_x':('if ((owner[0x74] & 8) == 0)','if (complete && (owner[0x74] & 8) == 0)'),
        'accept_equality':('D_800A57A4 <','D_800A57A4 <='),
        'accept_unordered':('*(f32 *)(payload + 8) * D_800A57A4 < *(f32 *)(owner + 0x2C)',
            '!(*(f32 *)(payload + 8) * D_800A57A4 >= *(f32 *)(owner + 0x2C))'),
        'wrong_y_target':('payload + 0x18','payload + 8'),
        'wrong_next_slot':('owner[0x70], 4,','owner[0x70], 5,'),
        'wrong_fifth_argument':('owner[0x72], owner[0x73]','owner[0x72], owner[0x72]')}
    result={n:b.replace(a,z,1) for n,(a,z) in changes.items()}
    if any(v==b for v in result.values()):raise ValueError('Ineffective extent control')
    return result
