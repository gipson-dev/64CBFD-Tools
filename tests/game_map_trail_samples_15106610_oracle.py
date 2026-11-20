"""Bounded interior samples with live providers and retained private output homes."""
from dataclasses import dataclass
import itertools
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

ENTRY,RECORD,SEGMENTS,POINTS=0x15106610,0x30000,0x50000,0x60000
GET_SEGMENTS,GET_POINTS,INTEGER,FLOAT,POLAR=0x151061E0,0x151061EC,0x150ADA20,0x150ADA68,0x15143874
COUNTS={GET_SEGMENTS:1,GET_POINTS:1,INTEGER:0,FLOAT:0,POLAR:4}
u32=lambda n:n&0xFFFFFFFF
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))

@dataclass(frozen=True)
class Case:
    count:int=1
    seed:int=0
    mode:int=0
    phase:int=0
    angle:int=-1

def cases():
    for row in itertools.product((0,1,2,4),range(8),range(4),(0,8)):yield Case(*row)
    for angle,phase in itertools.product(range(256),(0,8)):yield Case(1,angle%8,angle%4,phase,angle)

def integer(c,ordinal):
    base=(0,1,0xFFFFFFFF,0x80000000,0x876543FF,0xFF000080,0x7FFFFFFF,0x1234007F)[c.seed]if c.angle<0 else 0xA5A50000|c.angle
    return u32(base+(ordinal-1)*0x1000201)

def unit(c,ordinal):return bits((0.,-0.,0.25,0.75,-0.5,1.,-1.,2.)[(c.seed+ordinal-1)%8])
def xy(angle,radius):
    first=add(bits((angle-128)*0.125),mul(radius,bits(0.25)))
    second=add(bits((64-angle)*0.25),mul(radius,bits(-0.125)))
    return first,second

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
    for base,length in((RECORD-16,0xB0),(SEGMENTS-16,0x120),(POINTS-16,0x80)):
        m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(length)})
    put(m,RECORD+0x48,c.count)
    put(m,RECORD+0x4C,bits((0.,-0.,1.25,-2.5,17.,0.5,4.,0.125)[c.seed]))
    for i in range(12):put(m,RECORD+0x14+4*i,bits((i-5)*(c.seed+1)*0.125))
    for segment in range(4):
        for lane in range(13):put(m,SEGMENTS+52*segment+4*lane,bits((segment+1)*(lane-5)*(c.seed+1)*0.0625))
    return m

def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def frame(m,c):return bytes(m[STACK+c.phase-112+i]for i in range(136))

def effect(m,c,target,ordinal,args,retained):
    segment=SEGMENTS+(ordinal-1)*52
    if target==GET_SEGMENTS and c.mode&1:put(m,RECORD+0x4C,bits(15.5))
    elif target==GET_POINTS and c.mode&2:put(m,RECORD+0x14,bits(-37.5))
    elif target==INTEGER:
        if c.mode&1:
            put(m,RECORD+0x4C,bits(3.25));put(m,segment+28,bits(2.))
            if retained:
                put(m,retained[0],bits(7.5));put(m,retained[1],bits(-3.75))
    elif target==FLOAT:
        if c.mode&2:
            put(m,RECORD+0x4C,bits(-2.5));put(m,segment+44,bits(11.))
            if retained:put(m,retained[0],bits(-9.25))
    elif target==POLAR:
        if c.mode==3:
            put(m,RECORD+0x48,min(c.count,2));put(m,segment+12,bits(13.+ordinal))

def reference(initial,c):
    m,calls,snapshots,counts,retained=dict(initial),[],[],{},None
    first,second=STACK+c.phase-32,STACK+c.phase-28
    def call(target,*args):
        nonlocal retained
        args=tuple(map(u32,args));calls.append((target,args))
        ordinal=counts[target]=counts.get(target,0)+1
        if target==POLAR:
            snapshots.append((read(m,first),read(m,second)))
        effect(m,c,target,ordinal,args,retained)
        if target==GET_SEGMENTS:return SEGMENTS
        if target==GET_POINTS:return POINTS
        if target==INTEGER:return integer(c,ordinal)
        if target==FLOAT:return unit(c,ordinal)
        x,y=xy(args[0],args[1]);put(m,args[2],x);put(m,args[3],y);retained=args[2:]
    segments=call(GET_SEGMENTS,RECORD);points=call(GET_POINTS,RECORD)
    for axis in range(3):put(m,points+4*axis,read(m,RECORD+0x14+4*axis))
    count=signed(read(m,RECORD+0x48))
    for axis in range(3):put(m,points+(count+1)*12+4*axis,read(m,RECORD+0x38+4*axis))
    i=1
    if signed(u32(signed(read(m,RECORD+0x48))+1))>=2:
        while True:
            point=points+i*12;segment=segments+(i-1)*52
            random=call(INTEGER);sample=call(FLOAT)
            radius=mul(sample,read(m,RECORD+0x4C))
            call(POLAR,random&255,radius,first,second)
            for axis in range(3):
                value=add(add(mul(read(m,segment+28+4*axis),read(m,first)),
                              mul(read(m,segment+40+4*axis),read(m,second))),read(m,segment+4+4*axis))
                put(m,point+4*axis,value)
            i+=1
            if i>signed(read(m,RECORD+0x48)):break
    return m,calls,snapshots

class SampleOracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.case=c;self.counts={};self.retained=None;self.snapshots=[]
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(RECORD,))
    def record_call(self,target):
        assert target in COUNTS,hex(target)
        args=tuple(map(u32,self.arguments(COUNTS[target])))
        self.calls.append((target,args));self.counts[target]=self.counts.get(target,0)+1
        if target==POLAR:
            assert args[2:]==(STACK+self.case.phase-32,STACK+self.case.phase-28)
            self.snapshots.append(tuple(read(self.memory,p)for p in args[2:]))
    def hook(self,target):
        args=self.calls[-1][1];ordinal=self.counts[target]
        effect(self.memory,self.case,target,ordinal,args,self.retained)
        value=SEGMENTS if target==GET_SEGMENTS else POINTS if target==GET_POINTS else integer(self.case,ordinal)if target==INTEGER else 0xDEADBEEF
        if target==POLAR:
            x,y=xy(args[0],args[1]);put(self.memory,args[2],x);put(self.memory,args[3],y);self.retained=args[2:]
        for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=u32(value)
        if target==FLOAT:self.f[0]=unit(self.case,ordinal)
        self.hi,self.lo=0xA5000010,0xA5000011

def run(words,retail):
    covered=[set(),set()];count=0;angles=set()
    for c in cases():
        initial=fixture(c);want,calls,snapshots=reference(initial,c);models=[]
        for side,body in enumerate((words,retail)):
            got=SampleOracle(body,initial,c).run()
            assert public(got.memory)==public(want),(c,side,'public output')
            assert got.calls==calls,(c,side,'ABI trace')
            assert got.snapshots==snapshots,(c,side,'exposed float bytes')
            covered[side].update(got.visits);models.append(got)
        assert frame(models[0].memory,c)==frame(models[1].memory,c),(c,'complete private frame')
        angles.update(args[0]for target,args in calls if target==POLAR)
        count+=1
    return dict(cases=count,visited_words=[len(s)for s in covered],angles=len(angles),frame_bytes=136,
                exact_passed_homes=True,retained_pointer_mutations=True,provider_models=True,
                original_provider_bodies_executed=False,ordinary_finite_FP_contract=True,hardware_or_gameplay_claim=False)
