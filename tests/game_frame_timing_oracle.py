"""Bounded IEEE-single timing model with big-endian overlapping history labels."""
import itertools
import math
from collections import Counter

from tools.experiments import game_frame_timing_update as source
from tools.tests import game_view_render_pass_oracle as machine
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

put,read,STACK=machine.put,machine.read,machine.STACK
BASE,LENGTH,HISTORY,FACTOR,FINAL=0x800BE5D0,0x450,0x800BE5E8,0x800968D0,0x150A019C
PHASE,REMAINDER,INDEX,SAMPLES,HALF,TIME,INV,TOTAL,MOD,MEAN,MEAN_INV,TICKS,SNAPSHOT,DIVISOR=(
    0x800BE5E0,0x800BE610,0x800BE619,0x800BE61A,0x800BE9A0,0x800BE9A4,0x800BE9A8,
    0x800BE9AC,0x800BE9B0,0x800BE9B8,0x800BE9BC,0x800BE9E4,0x800BEA08,0x800BEA0C)


def hist(pattern):
    values=((1.0,)*10,tuple((i-5)*0.25 for i in range(10)),
        (1e20,1.0,-1e20,1.0,1e20,-1e20,2.0,3.0,4.0,5.0),
        tuple(-floating(1) if i==4 else 0.0 for i in range(10)),
        (-floating(1),)*10,(floating(0x7F7FFFFF),)*10)
    return tuple(bits(v) for v in values[pattern%len(values)])


def fixture(ticks=1,divisor=0,remainder=0,phase=0,index=0,samples=0,pattern=0,total=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    memory.update({BASE+i:0xA5 for i in range(LENGTH)})
    for address,value in ((TICKS,ticks),(REMAINDER,remainder),(TOTAL,total),(SNAPSHOT,0x87654321),
            (TIME,0x80000000),(INV,0x3E800000),(MEAN,0xBF800000),(MEAN_INV,0x3F800000),(MOD,0xDEADBEEF)):
        put(memory,address,value&0xFFFFFFFF)
    for address,value in ((DIVISOR,divisor),(PHASE,phase),(INDEX,index),(SAMPLES,samples),(HALF,0xA5)):
        memory[address]=value
    for i,value in enumerate(hist(pattern)):put(memory,HISTORY+i*4,value)
    put(memory,FACTOR,0x3DCCCCCD)
    return memory


def public(memory):
    return {a:b for a,b in memory.items() if not STACK-0x400<=a<STACK+0x100}


def digest(memory):
    value=2166136261
    for i in range(LENGTH//4):value=((value^read(memory,BASE+i*4))*16777619)&0xFFFFFFFF
    return value


def effect(memory,mode):
    if mode==1:put(memory,TICKS,0x87654321);put(memory,MEAN_INV,0x80000000)
    elif mode==2:memory[INDEX]=255;memory[SAMPLES]=0


def reference(initial,mode=0):
    memory=dict(initial);divisor=memory[DIVISOR];ticks=read(memory,TICKS)
    put(memory,SNAPSHOT,ticks)
    if divisor:
        if divisor==1:
            ticks=0;put(memory,TICKS,0);memory[PHASE]=0;put(memory,TIME,0)
        else:
            total=(read(memory,REMAINDER)+ticks)&0xFFFFFFFF
            ratio=bits(floating(bits(float(signed(ticks))))/floating(bits(float(divisor))))
            put(memory,TIME,ratio)
            ticks=math.trunc(floating(ratio))&0xFFFFFFFF;put(memory,TICKS,ticks)
            put(memory,TIME,bits(floating(ratio)*0.5))
            if total>=divisor:
                ticks=total//divisor;put(memory,TICKS,ticks)
                put(memory,REMAINDER,(total-ticks*total)&0xFFFFFFFF)
            else:put(memory,REMAINDER,total);ticks=0;put(memory,TICKS,0)
    else:put(memory,TIME,bits(floating(bits(float(signed(ticks))))*0.5))
    memory[PHASE]&=1
    memory[PHASE]=(memory[PHASE]+ticks)&255
    memory[HALF]=memory[PHASE]>>1
    value=floating(read(memory,TIME))
    if value!=0.0:put(memory,INV,bits(1.0/value))
    else:put(memory,TIME,0);put(memory,INV,0)
    total=(read(memory,TOTAL)+ticks)&0xFFFFFFFF;put(memory,TOTAL,total)
    value=signed(total);put(memory,MOD,(value-(abs(value)//30)*(-30 if value<0 else 30))&0xFFFFFFFF)
    index=memory[INDEX];put(memory,HISTORY+index*4,read(memory,TIME))
    memory[INDEX]=(index+1)&255
    if memory[INDEX]==10:memory[INDEX]=0
    if memory[SAMPLES]<10:
        memory[SAMPLES]+=1;put(memory,MEAN,read(memory,TIME));put(memory,MEAN_INV,read(memory,INV))
    else:
        total=bits(0.0)
        for i in range(10):total=bits(floating(total)+floating(read(memory,HISTORY+i*4)))
        mean=bits(floating(total)*floating(read(memory,FACTOR)));put(memory,MEAN,mean)
        value=floating(mean);put(memory,MEAN_INV,bits(1.0/value) if value!=0.0 else 0)
    observation=digest(memory);effect(memory,mode)
    return memory,[(FINAL,())],[observation]


def corpus():
    for ticks,divisor,remainder,phase,index,samples,mode in itertools.product(
            (0,1,30,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,3,255),(0,0xFFFFFFFE),
            (0,255),(0,9,12,240,255),(9,10),(0,1)):
        pattern=(index+ticks)%4;total=(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[pattern]
        args=(ticks,divisor,remainder,phase,index,samples,pattern,total)
        yield fixture(*args),mode,args
    for byte in range(256):
        for field in (DIVISOR,PHASE,INDEX,SAMPLES):
            args=[0xFFFFFFFF,3,1,255,9,10,byte%4,0x7FFFFFFF]
            args[{DIVISOR:1,PHASE:3,INDEX:4,SAMPLES:5}[field]]=byte
            yield fixture(*args),2,tuple(args)
    for pattern,index in itertools.product((4,5),(0,9,255)):
        args=(0,0,0,0,index,10,pattern,0)
        yield fixture(*args),0,args


class TimingOracle(machine.RenderOracle):
    def __init__(self,words,memory,mode=0,phase=0,entry=source.ENTRY,arguments=None,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=arguments or (0x12345678,),connected=connected)
        self.timing_mode=mode;self.hi=0

    def execute(self,word):
        op,fn,rs,rt,rd=word>>26,word&63,word>>21&31,word>>16&31,word>>11&31
        if op==0 and fn in (16,25,26,27):
            if fn==16:self.r[rd]=self.hi
            elif fn==25:
                value=self.r[rs]*self.r[rt];self.lo=value&0xFFFFFFFF;self.hi=(value>>32)&0xFFFFFFFF
            else:
                left,right=(signed(self.r[rs]),signed(self.r[rt])) if fn==26 else (self.r[rs],self.r[rt])
                assert right,'Unreachable zero divisor'
                value=(abs(left)//abs(right))*(-1 if (left<0)!=(right<0) else 1)
                self.lo=value&0xFFFFFFFF;self.hi=(left-value*right)&0xFFFFFFFF
            self.r[0]=0
        else:super().execute(word)

    def record_call(self,target):
        assert target==FINAL
        self.calls.append((target,()));self.events.append(('CALL',target,()))
        self.observations.append(digest(self.memory))

    def hook(self,target):
        assert target==FINAL;effect(self.memory,self.timing_mode)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.lo,self.hi=0xA5000010,0xA5000011
