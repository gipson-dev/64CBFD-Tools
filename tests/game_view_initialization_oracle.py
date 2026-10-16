"""Opaque-provider contracts for view startup, not allocator or renderer emulation."""
import itertools
import math

from tools.experiments import game_view_initialization as source
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_view_render_pass_oracle import RenderOracle, put, read, STACK

BASE, LENGTH, COUNT, CATEGORY = 0x800BE600, 0x100, 0x80082FA0, 0x800BE9F0
FIRST, SECOND, HEIGHT, BIAS, FACTOR = 0x800BE628, 0x800BE62C, 0x800BE63C, 0x800BE6B8, 0x800968E0
FLAGS = (0x800BE617, 0x800BE614, 0x800BE635)
ALLOCATE, CLEANUP, VIEW, FINAL = 0x10003C40, 0x150006E0, 0x1501A8C0, 0x1510B070
SIGNATURES = {ALLOCATE:4, CLEANUP:1, VIEW:4, FINAL:1}


def fixture(count=1, height=240, mode=0):
    memory = {STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    memory.update({BASE+i:0xA5 for i in range(LENGTH)})
    put(memory,COUNT,count&0xFFFFFFFF)
    put(memory,CATEGORY,0x87654321)
    put(memory,HEIGHT,height&0xFFFFFFFF)
    put(memory,BIAS,0xBF800000)
    put(memory,FACTOR,0x3F4CCCCD)
    return memory


def canonical(value):
    return 0x7FC00000 if value&0x7F800000==0x7F800000 and value&0x7FFFFF else value


def public(memory):
    result = {a:b for a,b in memory.items() if not STACK-0x400<=a<STACK+0x100}
    put(result,BIAS,canonical(read(result,BIAS)))
    return result


def digest(memory):
    value = 2166136261
    values = [read(memory,COUNT),read(memory,CATEGORY)] + [read(memory,BASE+i) for i in range(0,LENGTH,4)]
    values[2+(BIAS-BASE)//4] = canonical(values[2+(BIAS-BASE)//4])
    for word in values:
        value = ((value^word)*16777619)&0xFFFFFFFF
    return value


def effect(memory,target,ordinal,mode):
    if target==ALLOCATE:
        if mode==1 and ordinal==1:
            put(memory,COUNT,1);put(memory,HEIGHT,7);put(memory,CATEGORY,0x13579BDF)
        if mode==2 and ordinal==2:
            put(memory,COUNT,0);put(memory,HEIGHT,0x80000000)
        return (0 if ordinal==1 else 0xFFFF1234) if mode==8 else 0x81400000+ordinal*0x1000
    if target==CLEANUP:
        if mode==3:put(memory,COUNT,2)
        if mode==7:put(memory,COUNT,1)
        if mode==9:put(memory,FIRST,0xDEADC0DE)
    if target==VIEW:
        if mode==4 and ordinal<=2:put(memory,COUNT,3 if ordinal==1 else 0)
        if mode==5 and ordinal==1:put(memory,COUNT,0xFFFFFFFF)
    if target==FINAL and mode==6:
        for a,v in zip(FLAGS,(0xA1,0xB2,0xC3)):memory[a]=v
        put(memory,COUNT,0x87654321);put(memory,BIAS,0x80000000)
    return 0xB5000000+(target&65535)


def reference(initial,count,projection_mode,mode=0,limit=None):
    memory = dict(initial)
    calls,observations,counts = [],[],{}
    def call(target,*args):
        ordinal = counts.get(target,0)+1;counts[target]=ordinal
        calls.append((target,tuple(v&0xFFFFFFFF for v in args)))
        observations.append(digest(memory))
        if target==VIEW and ordinal==limit:raise CallLimit
        return effect(memory,target,ordinal,mode)
    put(memory,COUNT,count&0xFFFFFFFF)
    slots = 1 if not count&0xFFFFFFFF else (count+2)&0xFFFFFFFF
    put(memory,FIRST,call(ALLOCATE,(slots*384)&0xFFFFFFFF,1,1,0))
    put(memory,SECOND,call(ALLOCATE,(slots*16)&0xFFFFFFFF,1,1,0))
    if read(memory,COUNT)==1:
        height = bits(floating(bits(float(signed(read(memory,HEIGHT)))))-2.0)
        scaled = bits(floating(height)*floating(read(memory,FACTOR)))
        rounded = math.trunc(floating(scaled))
        remainder = (abs(rounded)%4)*(-1 if rounded<0 else 1)
        numerator = floating(bits(float(rounded-remainder)))
        value = numerator/floating(height) if floating(height) else math.nan
        put(memory,BIAS,bits(value))
    call(CLEANUP,read(memory,CATEGORY))
    index = 0
    try:
        while signed(index)<=signed(read(memory,COUNT)):
            call(VIEW,index,read(memory,COUNT),1023,0)
            index = (index+1)&0xFFFFFFFF
        if read(memory,COUNT):call(VIEW,index,0,1023,0)
    except CallLimit:
        return memory,calls,observations,False
    for a,v in zip(FLAGS,(1,1,0)):memory[a]=v
    call(FINAL,projection_mode)
    return memory,calls,observations,True


def corpus():
    for count,height,mode in itertools.product((-0x80000000,-2,-1,0,1,2,4),
            (-0x80000000,-101,-7,-1,0,1,2,3,6,7,240,0x7FFFFFFF),range(10)):
        projection = (0,1,0x80000000,0xFFFFFFFF)[(count+height+mode)%4]
        yield fixture(count,height),count,projection,mode
    for count,mode in itertools.product((0x7FFFFFFF,0x40000000,0xFFFFFFFE,0xFFFFFFFF),(2,3,7)):
        yield fixture(count,3),count,0x87654321,mode


class CallLimit(Exception):
    pass


class InitializationOracle(RenderOracle):
    def __init__(self,words,memory,count,projection_mode,mode=0,phase=0,entry=source.ENTRY,connected=None,limit=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(count&0xFFFFFFFF,projection_mode&0xFFFFFFFF),connected=connected)
        self.provider_mode,self.limit = mode,limit
        self.provider_counts = {}

    def record_call(self,target):
        assert target in SIGNATURES,hex(target)
        args = self.arguments(SIGNATURES[target])
        self.calls.append((target,args));self.observations.append(digest(self.memory))
        self.events.append(('CALL',target,args))
        self.provider_counts[target] = self.provider_counts.get(target,0)+1
        if target==VIEW and self.provider_counts[target]==self.limit:raise CallLimit

    def hook(self,target):
        result = effect(self.memory,target,self.provider_counts[target],self.provider_mode)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = result&0xFFFFFFFF
