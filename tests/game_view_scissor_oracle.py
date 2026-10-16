"""Ordered float32 scissor reference; invalid conversion stops before the cast."""
import itertools
import math

from tools.experiments import game_view_scissor_setup as source
from tools.tests.game_view_render_pass_oracle import RenderOracle, STACK, put, read
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests import test_game_actor_burst_consumer_match as faults

GLOBALS,GLOBAL_BYTES=0x800BE600,0x100
WIDTH,HEIGHT,BASE=0x800BE620,0x800BE624,0x800BE628
VIEWS,RECORD_BASE,RECORD_BYTES=0x30000,0x2FD00,8*0x180
OUTPUT,OUTPUT_BYTES=0x20000,128
CLAMP=0x1501AF44
CLAMP_DEAD={0x1501AFA0,0x1501AFF4,0x1501B044,0x1501B090}
REGIONS=((GLOBALS,GLOBAL_BYTES),(RECORD_BASE,RECORD_BYTES),(OUTPUT,OUTPUT_BYTES))


class ConversionBoundary(Exception):pass


def half(word):return ((word&65535)^0x8000)-0x8000


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x100}


def quantize(word):
    value=floating(bits(floating(word)*4.0))
    if not math.isfinite(value) or not -0x80000000<=value<0x80000000:raise ConversionBoundary
    return math.trunc(value)&4095


def clamp_edge(word,minimum,maximum):
    if floating(word)<minimum:return bits(minimum)
    return maximum if floating(maximum)<floating(word) else word


def reference(initial,args):
    memory=dict(initial);cursor=args[0];view=half(args[1]);observations=[];writes=[]
    def store(address,value):
        put(memory,address,value);writes.append(address)
    store(cursor,0xE7000000);store(cursor+4,0);cursor+=8
    try:
        if view==255:
            store(cursor,0xED008000)
            right=bits(float(signed((read(memory,WIDTH)-2)&0xFFFFFFFF)))
            bottom=bits(float(signed(read(memory,HEIGHT))))
            value=(args[5]&3)<<24|quantize(right)<<12|quantize(bottom)
            store(cursor+4,value)
        else:
            record=(read(memory,BASE)+view*0x180)&0xFFFFFFFF
            if not all(record+offset+i in memory for offset in (0x24,0x28,0x2C,0x30) for i in range(4)):
                raise KeyError('Unmapped view record after pipe-sync alias')
            left,right,top=(read(memory,record+offset) for offset in (0x2C,0x30,0x24))
            bottom=read(memory,record+0x28)
            if args[4]&0xFFFFFFFF:
                limit=bits(float(signed(args[4]&0xFFFFFFFF)))
                if floating(limit)<floating(bottom):bottom=limit
            observations.append((left,top,right,bottom))
            maximum=bits(floating(bits(float(signed(read(memory,WIDTH)))))-2.0)
            left=clamp_edge(left,2.0,maximum);right=clamp_edge(right,2.0,maximum)
            maximum=bits(float(signed(read(memory,HEIGHT))))
            top=clamp_edge(top,0.0,maximum);bottom=clamp_edge(bottom,0.0,maximum)
            store(cursor,0xED000000|quantize(left)<<12|quantize(top))
            store(cursor+4,(args[5]&3)<<24|quantize(right)<<12|quantize(bottom))
    except ConversionBoundary:
        return memory,observations,writes,False,None
    return memory,observations,writes,True,cursor+8


def fixture(view=0,width=292,height=216,coords=(4.25,5.5,200.75,180.25),limit=0,mode=0,output=None):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,size in REGIONS:memory.update({base+i:0xA5 for i in range(size)})
    row=(VIEWS+half(view)*0x180)&0xFFFFFFFF
    memory.update({row+i:0xA5 for i in range(0x180)})
    for at,value in ((WIDTH,width),(HEIGHT,height),(BASE,VIEWS)):put(memory,at,value&0xFFFFFFFF)
    for at,value in zip((0x2C,0x24,0x30,0x28),coords):put(memory,row+at,value if isinstance(value,int) else bits(value))
    args=(OUTPUT+32 if output is None else output,view&0xFFFFFFFF,0x87654321,0x12345678,limit&0xFFFFFFFF,mode&0xFFFFFFFF)
    return memory,args


def corpus():
    patterns=((292,216,(4.25,5.5,200.75,180.25)),(320,240,(-5.,-7.,500.,1000.)),
        (1,-1,(-0.,-0.,2.,-0.)),(-7,-3,(2.,1.,10.,20.)),
        (16777217,1048577,(17.,91.,1000.25,200.5)),(-0x80000000,0x7FFFFFFF,(0.,0.,128.,72.)),
        (292,216,(0x7FC12345,0.,10.,10.)),(292,216,(math.inf,-math.inf,10.,-0.)),
        (292,216,(25.,5.,200.,0x7FC56789)))
    for view,pattern,limit,mode in itertools.product((0,1,3,-1,0x8000,32767,255,0x100FF,0x10000,0x10001,0x1FFFF),
            patterns,(0,1,-1,0x7FFFFFFF),(0,1,3,0x80000003)):
        memory,args=fixture(view,*pattern,limit,mode)
        yield memory,args,(pattern[0],pattern[1],tuple(bits(x) if not isinstance(x,int) else x for x in pattern[2]))
    for view,pattern,limit,mode in itertools.product((0,1,255,-1),patterns[:3],(0,128,-1),(0,3)):
        row=(VIEWS+half(view)*0x180)&0xFFFFFFFF
        for output in (WIDTH-4,WIDTH,HEIGHT,row+0x1C,row+0x24,row+0x2C):
            memory,args=fixture(view,*pattern,limit,mode,output)
            try:reference(memory,args)
            except KeyError:continue
            yield memory,args,(pattern[0],pattern[1],tuple(bits(x) for x in pattern[2]))


class ScissorOracle(RenderOracle):
    def __init__(self,words,memory,args,clamp,phase=0,entry=source.ENTRY,connected=None):
        self.all_accesses=0;self.access_fault=None
        code={CLAMP+i*4:w for i,w in enumerate(clamp)}
        code.update(connected or {})
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=code)

    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.access_fault:raise faults.AccessBoundary
            self.all_accesses+=1
        super().access()

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            value=floating(self.f[word>>11&31])
            if not math.isfinite(value) or not -0x80000000<=value<0x80000000:raise ConversionBoundary
        super().execute(word)

    def record_call(self,target):
        if target==CLAMP:
            args=self.arguments(4)
            self.calls.append((target,args))
            self.observations.append(tuple(read(self.memory,a) for a in args))
        elif target==source.ENTRY:self.calls.append((target,self.arguments(6)))
        else:raise AssertionError('Unexpected scissor provider '+hex(target))

    def hook(self,target):raise AssertionError('Scissor helper must be connected')
