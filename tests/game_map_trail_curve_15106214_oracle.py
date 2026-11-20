"""Bounded curve sampling with observable provider calls and single precision."""
from dataclasses import dataclass
import itertools
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

ENTRY,RECORD,OUTPUT=0x15106214,0x30000,0x50000
GETTER,FRAME=0x151061E0,0x15146078
BASIS=(0x151064B4,0x151064DC,0x15106510,0x15106540,0x15106558,0x15106584,0x151065BC,0x151065EC)
u32=lambda x:x&0xFFFFFFFF

@dataclass(frozen=True)
class Case:
    count:int
    seed:int
    mode:int
    phase:int

def cases():
    for row in itertools.product((-2,0,1,2,4),range(8),range(4),(0,8)):
        yield Case(*row)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
    for base,length in((RECORD-16,0xB0),(OUTPUT-16,0x200)):
        m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(length)})
    put(m,RECORD+0x48,c.count)
    put(m,RECORD+0x64,bits((0.,0.25,0.5,-0.25,1.,-0.,0.125,0.33333334)[c.seed]))
    for i in range(12):put(m,RECORD+0x14+4*i,bits((i-5)*(c.seed+1)*0.125))
    return m

def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
def blob(m,p,n):return bytes(m[p+i]for i in range(n))
def weight(c,index,parameter):
    # Distinct finite provider results exercise all eight live values. Original
    # polynomial-provider execution is a separate connected-code check.
    return bits((index+1)*(c.seed+1)*0.0625+floating(parameter)*0.125)

def effect(m,c,target,ordinal,args):
    if target==GETTER and c.mode&1:
        put(m,RECORD+0x64,bits(0.375))
    if target==BASIS[-1]and c.mode&1:
        put(m,RECORD+0x14,bits(17.+ordinal))
        put(m,RECORD+0x3C,bits(-11.-ordinal))
    if target==FRAME:
        tangent,normal,binormal=args
        put(m,tangent+4,read(m,tangent+4)^0x80000000)
        for i in range(3):
            put(m,normal+4*i,bits((ordinal+i+1)*0.25))
            put(m,binormal+4*i,bits(-(ordinal+i+1)*0.5))
        if c.mode&2:
            # Count is reloaded, but the increment remains the cached value.
            put(m,RECORD+0x48,min(max(c.count,0),2))
            put(m,RECORD+0x64,bits(7.))
            put(m,RECORD+0x20,bits(23.+ordinal))

def returned(c,target,ordinal,parameter=None):
    if target==GETTER:return OUTPUT
    if target==FRAME:return 0 if(c.seed+ordinal)&1 else 0x80000000
    return weight(c,BASIS.index(target),parameter)

def coordinate(m,axis,weights):
    products=[bits(floating(read(m,RECORD+0x14+i*12+axis*4))*floating(weights[i]))for i in range(4)]
    first=bits(floating(products[0])+floating(products[1]))
    second=bits(floating(first)+floating(products[2]))
    return bits(floating(products[3])+floating(second))

def reference(initial,c):
    m,calls,snapshots,counts=dict(initial),[],[],{}
    def call(target,*args):
        args=tuple(map(u32,args));calls.append((target,args))
        ordinal=counts[target]=counts.get(target,0)+1
        if target==FRAME:snapshots.append(blob(m,args[0],36))
        effect(m,c,target,ordinal,args)
        return returned(c,target,ordinal,args[0]if target in BASIS else None)
    segment=call(GETTER,RECORD)
    step=read(m,RECORD+0x64);parameter=step;i=0
    if signed(read(m,RECORD+0x48))>0:
        while True:
            put(m,segment,parameter)
            values=[call(target,parameter)for target in BASIS]
            for axis in range(3):put(m,segment+4+4*axis,coordinate(m,axis,values[:4]))
            for axis in range(3):put(m,segment+16+4*axis,coordinate(m,axis,values[4:]))
            ok=call(FRAME,segment+16,segment+28,segment+40)
            if ok==0:
                for lane in range(6):put(m,segment+28+4*lane,0)
            i+=1
            limit=signed(read(m,RECORD+0x48))
            segment+=52
            parameter=bits(floating(parameter)+floating(step))
            if i>=limit:break
    return m,calls,snapshots

class CurveOracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.case=c;self.counts={};self.snapshots=[]
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(RECORD,))
    def record_call(self,target):
        assert target in(*BASIS,GETTER,FRAME),hex(target)
        args=(self.f[12],)if target in BASIS else tuple(self.arguments(1 if target==GETTER else 3))
        self.calls.append((target,args))
        self.counts[target]=self.counts.get(target,0)+1
        if target==FRAME:self.snapshots.append(blob(self.memory,args[0],36))
    def hook(self,target):
        args=self.calls[-1][1];ordinal=self.counts[target]
        effect(self.memory,self.case,target,ordinal,args)
        value=returned(self.case,target,ordinal,args[0]if target in BASIS else None)
        for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        if target in BASIS:self.f[0]=value
        else:self.r[2]=value
        self.hi,self.lo=0xA5000010,0xA5000011

def run(words,retail):
    covered=[set(),set()];count=0
    for c in cases():
        initial=fixture(c);want,calls,snapshots=reference(initial,c)
        for side,body in enumerate((words,retail)):
            got=CurveOracle(body,initial,c).run()
            assert public(got.memory)==public(want),(c,side,'public output')
            assert got.calls==calls,(c,side,'call trace')
            assert got.snapshots==snapshots,(c,side,'frame arguments')
            covered[side].update(got.visits)
        count+=1
    return dict(cases=count,visited_words=[len(s)for s in covered],provider_models=True,
                original_provider_bodies_executed=False,hardware_or_gameplay_claim=False)
