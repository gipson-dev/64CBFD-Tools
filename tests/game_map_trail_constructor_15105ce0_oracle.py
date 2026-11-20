"""Bounded constructor contracts; providers are modeled, not gameplay emulation."""
from dataclasses import dataclass
import itertools
import struct
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating, signed

ENTRY = 0x15105CE0
PACKET, OUTPUT, VECTOR, LIMIT, SCALE = 0x30000, 0x50000, 0x800A5480, 0x800A2410, 0x800A2414
ALLOCATE, COPY, RNG, CURVE, SAMPLES, ZERO, CHILD = 0x15167A68, 0x10022EC0, 0x150ADA20, 0x15106214, 0x15106610, 0x100226F0, 0x15130280
COUNTS = {ALLOCATE: 6, COPY: 3, RNG: 0, CURVE: 1, SAMPLES: 1, ZERO: 2, CHILD: 6}
u32 = lambda n: n & 0xFFFFFFFF
half = lambda n: ((n & 65535) ^ 32768) - 32768

@dataclass(frozen=True)
class Case:
    pieces: int = 1
    success: int = 1
    seed: int = 0
    mode: int = 0
    phase: int = 0

def cases():
    for p, ok, seed, mode, phase in itertools.product((0, 1, 7, 31), (0, 1), range(8), range(4), (0, 8)):
        yield Case(p, ok, seed, mode, phase)

def arguments(c):
    return (PACKET, (0, 4, 64, 256)[c.seed % 4], (0x12340000, 0x12340001, 0xFFFFFF80, 0xFFFFFFFF)[c.seed % 4], u32((-1, 0, 2, 127)[c.seed % 4]))

def fixture(c):
    m = {STACK+i: (i*17+c.seed*13+0xA5) & 255 for i in range(-1024, 256)}
    for base, n in ((PACKET-16, 112), (OUTPUT-16, 4096), (VECTOR, 12), (LIMIT, 8)):
        m.update({base+i: (i*29+c.seed*11+0x5A)&255 for i in range(n)})
    for i in range(12): put(m, PACKET+4+i*4, bits((i-5)*(c.seed+1)*0.25))
    put(m, PACKET+0x38, c.pieces)
    put(m, PACKET+0x40, (0, 0xBF800000, 0x418A0000, 0x7149F2CA)[c.seed % 4])
    put(m, PACKET+0x44, (-32768, -1, 0, 32767)[c.seed % 4], 2)
    put(m, PACKET+0x46, (0, 32767, -32768, 7)[c.seed % 4], 2)
    for i, value in enumerate((0x80000000, 0x3F800000, 0xBF800000)): put(m, VECTOR+4*i, value)
    put(m, LIMIT, 0x49742400); put(m, SCALE, 0x3D9D89D9)
    return m

def data(m, p, n): return bytes(m[p+i] for i in range(n))
def write(m, p, b): m.update({p+i:v for i,v in enumerate(b)})
def public(m): return {a:b for a,b in m.items() if not STACK-1024 <= a < STACK+256}

def random_value(c, ordinal):
    return (0, 1, 0xFFFFFFFF, 0x80000000, 0, 0x87654321, 0, 7)[(c.seed+ordinal-1) % 8]

def provider_effect(m, c, target, ordinal, args):
    if target == ALLOCATE and c.mode & 1:
        put(m, PACKET+0x38, c.pieces+1)
    if target == RNG and ordinal == 1 and c.mode & 1:
        put(m, PACKET+0x44, -123, 2); put(m, PACKET+0x46, -32768, 2)
    if target == CURVE and c.mode & 2:
        put(m, OUTPUT+0x48, c.pieces+2)
        m[PACKET+0x48] ^= 0x55
    if target == SAMPLES and c.mode & 2:
        put(m, PACKET+0x40, 0x40200000)
        put(m, VECTOR+4, 0x40400000)
    if target == CHILD:
        # The second invocation must retain helper edits except position/flags.
        descriptor = args[0]
        put(m, descriptor+0x04, 0x12340000+ordinal)
        put(m, descriptor+0x28, 0x3F000000+ordinal)
        m[descriptor+0x67] ^= 0xA5
        put(m, PACKET+0x28, 0x42C80000+ordinal)

def reference(initial, c):
    m, calls, snapshots, counts = dict(initial), [], [], {}
    def call(target, *args):
        args = tuple(map(u32,args)); calls.append((target,args))
        ordinal = counts[target] = counts.get(target,0)+1
        if target == CHILD: snapshots.append(data(m,args[0],112))
        provider_effect(m,c,target,ordinal,args)
        return random_value(c,ordinal) if target == RNG else (0 if ordinal+c.seed & 1 else 0x70000+ordinal*0x100)
    _, extra, priority, context = arguments(c)
    n = read(m,PACKET+0x38); points = (n+2)*12
    call(ALLOCATE,64,context,n*52+points+extra+136,1,priority&255,1)
    if not c.success: return m,calls,0,snapshots
    call(COPY,OUTPUT+16,PACKET,80); write(m,OUTPUT+16,data(m,PACKET,80))
    put(m,OUTPUT+96,OUTPUT+n*52+points+136)
    put(m,OUTPUT+100,bits(1.0/floating(bits(float(signed(read(m,PACKET+56))+1)))))
    value=call(RNG); divisor=u32(half(read(m,PACKET+70,2))+1)
    assert divisor
    put(m,OUTPUT+104,value%divisor+half(read(m,PACKET+68,2)),2)
    call(CURVE,OUTPUT);call(SAMPLES,OUTPUT)
    put(m,OUTPUT+108,0);put(m,OUTPUT+112,0)
    call(ZERO,OUTPUT+116,16);write(m,OUTPUT+116,bytes(16))
    put(m,OUTPUT+132,read(m,OUTPUT+72)*48+96)
    descriptor=STACK+c.phase-128
    fields=((0,0x200005,4),(4,0,4),(8,0x4404,2),(10,300,2),(12,0,4),(16,0,4),
            (28,255,1),(29,43,1),(30,1,2),(32,255,2),(34,1,2),(36,0x3F800000,4),
            (84,0,4),(88,0xC000,4),(92,0,4),(96,6,1),(97,6,1),(98,255,1),
            (99,255,1),(100,255,1),(101,0,1),(102,255,1),(104,0,2),(108,read(m,LIMIT),4))
    for at,value,size in fields:put(m,descriptor+at,value,size)
    write(m,descriptor+20,bytes([255]*4));write(m,descriptor+24,data(m,PACKET+72,4))
    write(m,descriptor+60,data(m,VECTOR,12));write(m,descriptor+72,data(m,VECTOR,12))
    size=bits(floating(bits(floating(read(m,PACKET+64))*floating(read(m,SCALE))))*200.0)
    put(m,descriptor+40,size);put(m,descriptor+44,size)
    for i, point in enumerate((0,3)):
        write(m,descriptor+48,data(m,PACKET+4+point*12,12))
        first=64 if call(RNG) else 0
        flags=(128 if call(RNG) else 0)|first
        put(m,descriptor+88,flags)
        child=call(CHILD,descriptor,0,0,0,priority&255,context)
        put(m,OUTPUT+108+4*i,child)
    return m,calls,OUTPUT,snapshots

class ConstructorOracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.case=c
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=arguments(c))
        self.provider_counts={};self.snapshots=[]
    def record_call(self,target):
        assert target in COUNTS,hex(target)
        args=tuple(map(u32,self.arguments(COUNTS[target])))
        self.calls.append((target,args))
        self.provider_counts[target]=self.provider_counts.get(target,0)+1
        if target==CHILD:self.snapshots.append(data(self.memory,args[0],112))
    def hook(self,target):
        c=self.case;args=self.calls[-1][1];ordinal=self.provider_counts[target]
        provider_effect(self.memory,c,target,ordinal,args)
        if target==ALLOCATE:value=OUTPUT if c.success else 0
        elif target==COPY:
            write(self.memory,args[0],data(self.memory,args[1],args[2]));value=args[0]
        elif target==ZERO:write(self.memory,args[0],bytes(args[1]));value=0xDEADBEEF
        elif target==RNG:value=random_value(c,ordinal)
        else:value=0 if ordinal+c.seed&1 else 0x70000+ordinal*0x100
        for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def run(words,retail):
    covered=[set(),set()];count=0
    for c in cases():
        memory=fixture(c);want,calls,value,snapshots=reference(memory,c)
        for i,body in enumerate((words,retail)):
            m=ConstructorOracle(body,memory,c).run()
            assert (public(m.memory),m.calls,m.r[2],m.snapshots)==(public(want),calls,value,snapshots), (c,i,'constructor contract')
            covered[i].update(m.visits)
        count+=1
    return dict(cases=count,visited_words=[len(v) for v in covered],complete_112_byte_descriptors=True,
                modeled_provider_mutations=3,original_provider_bodies_executed=False,
                ordinary_valid_memory_only=True,hardware_or_gameplay_claim=False)
