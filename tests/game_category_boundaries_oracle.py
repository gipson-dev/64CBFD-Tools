"""Independent bounded category reference; no invalid stack/category C claims."""
from dataclasses import dataclass
import itertools
import struct

from tools.experiments import game_category_boundaries_candidates as source
from tools.tests import test_game_route_record_copy_match as core

STACK,put,read=core.STACK,core.put,core.read
ROWS=0x30000
DEFAULT={'D_80087290':0x80087290,'D_800D2350':0x800D2350,'D_800D2358':0x800D2358,
    'D_800D237C':0x800D237C,'D_800D2360':0x800D2360,
    'D_8009D9C0':0x8009D9C0,'D_8009D9C4':0x8009D9C4,'D_8009D9C8':0x8009D9C8}


def bits(value):return struct.unpack('>I',struct.pack('>f',value))[0]
def floating(value):return struct.unpack('>f',struct.pack('>I',value))[0]
def signed16(value):return (value&0x7FFF)-(value&0x8000)


@dataclass(frozen=True)
class Case:
    rows:tuple=()
    count:int|None=None
    seed:int=0
    poison:bool=False


def cases():
    for count in (-32768,-257,-1,0):
        for poison in (False,True):yield Case(count=count,poison=poison,seed=count&255)
    values=(-32768,-10001,-10000,-9999,-1,0,1,9999,10000,10001,32767)
    for category in range(6):
        for height in values:yield Case(((height,category),),seed=(height+category)&255)
    for mask in range(64):
        for mode in range(3):
            rows=[]
            for category in range(6):
                if mask>>category&1:
                    lo,hi=((category*500,category*500+50),(-32768,32767),(-10000,10000))[mode]
                    rows.extend(((hi,category),(lo,category),(lo,category)))
            if mode==1:rows.reverse()
            yield Case(tuple(rows),seed=mask)
    values=(-32768,-10001,-10000,-1,0,1,10000,10001,32767)
    for category in range(5):
        for left,right in itertools.product(values,repeat=2):
            yield Case(((left,category),(right,category+1)),seed=(left^right)&255)
    for count in (1,2,7,16,31,32):
        yield Case(tuple((((i*7919+32768)&65535)-32768,i%6) for i in range(count)),seed=count)


def fixture(case,phase=0,anchors=None,rows=ROWS):
    a=DEFAULT if anchors is None else anchors
    m={STACK+i:(i*17+case.seed+0xA5)&255 for i in range(-512,256)}
    for name in ('D_80087290','D_800D2350','D_800D2358','D_800D237C','D_800D2360'):
        m.update({a[name]+i:(i*37+case.seed*13+0xA5)&255 for i in range(-8,64)})
    m.update({rows+i:(i*137+case.seed*31+19)&255 for i in range(1024)})
    for i,(height,category) in enumerate(case.rows):
        put(m,rows+i*16+2,height,2);put(m,rows+i*16+6,category,1)
    count=len(case.rows) if case.count is None else case.count
    put(m,a['D_80087290'],count,2);put(m,a['D_800D2350'],1 if case.poison else rows,4)
    for name,value in (('D_8009D9C0',-10000.),('D_8009D9C4',10000.),('D_8009D9C8',100000.)):
        put(m,a[name],bits(value),4)
    return m


def reference(memory,anchors=None,trace=None):
    a=DEFAULT if anchors is None else anchors;m=memory.copy()
    low=[10000.]*6;high=[-10000.]*6
    count=signed16(read(m,a['D_80087290'],2))
    if count>0:
        rows=read(m,a['D_800D2350'],4)
        for i in range(count):
            height=signed16(read(m,rows+i*16+2,2));category=read(m,rows+i*16+6,1)
            if not 0<=category<6:raise ValueError('Outside bounded category reference')
            low[category]=min(low[category],height);high[category]=max(high[category],height)
    def store(at,value,size):
        put(m,at,value,size)
        if trace is not None:trace.append((at,size,value&((1<<(8*size))-1)))
    store(a['D_800D2358'],0,1);active=0;ids=[]
    for category,(lo,hi) in enumerate(zip(low,high)):
        if lo<=hi:
            ids.append(category);store(a['D_800D237C']+active,category,1)
            active+=1;store(a['D_800D2358'],active,1)
    overlap=0;written=0
    for first,second in zip(ids,ids[1:]):
        # Signed16 heights and the fixed extrema make this sum/half exact in f32.
        store(a['D_800D2360']+written*4,bits((low[second]+high[first])*0.5),4)
        overlap|=low[second]<high[first];written+=1
    store(a['D_800D2360']+written*4,bits(100000.),4)
    return int(overlap),m


def public(memory):return {a:v for a,v in memory.items() if not STACK-512<=a<STACK+256}


class BoundaryModel(core.CopyModel):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY):
        super().__init__(words,memory,(),phase=phase,entry=entry);self.requested=None

    def get(self,address,size):
        self.requested=('R',address,size);return super().get(address,size)

    def put(self,address,value,size):
        self.requested=('W',address,size);return super().put(address,value,size)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected category-boundary callee')
        self.caller_args.append(())

    def hook(self,target):raise ValueError('Category-boundary routine unexpectedly called a provider')
