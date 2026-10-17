"""Ordered three-clock-read reference, sparse aliases and bounded guest faults."""
import itertools
import math
from tools.experiments import game_transition_child_motion as source
from tools.tests import game_view_point_projection_oracle as point

bits,floating,add,mul,put,read,STACK=point.bits,point.floating,point.add,point.mul,point.put,point.read,point.STACK
RECORD=0x30020
CLOCK,DAMP_X,DAMP_Y=0x800BE9A4,0x800A0878,0x800A087C


def fixture(pattern=0,alias=0):
    addresses=(CLOCK,DAMP_X,DAMP_Y)
    record=RECORD if alias==0 else addresses[(alias-1)//6]-(0x10,0x14,0x70,0x74,0x78,0x7C)[(alias-1)%6]
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x500,0x120)}
    for base,length in ((record-16,160),(CLOCK-16,40),(DAMP_X-16,40)):
        memory.update({base+i:(i*13+0xA5)&255 for i in range(length)})
    values=((2.,-3.,4.,5.,0.5,0.),(-0.,0.,-1.,-2.,0.,-1.),
        (16777216.,1.,-16777216.,0.25,-0.5,1.),(0.,1.,0.,-0.,-0.,1.),
        (1.,2.,3.,4.,0.404,100.),(1.,2.,3.,4.,0.404,-100.),
        (0.,0.,1.,0.,0.,0.),(-3.,-2.,-1.,-4.,-0.5,-100.))[pattern%8]
    for at,value in zip((0x10,0x14,0x70,0x74,0x78,0x7C),values): put(memory,record+at,bits(value))
    for at,value in zip(addresses,(bits((0.,0.5,1.,-1.)[pattern%4]),0x3E99999A,0xBE19999A)):
        put(memory,at,value)
    return memory,(record,)


def reference(initial,args,clock=CLOCK,damp_x=DAMP_X,damp_y=DAMP_Y):
    memory=dict(initial); p=args[0]; vy=read(memory,p+0x74); acceleration=read(memory,p+0x78)
    put(memory,p+0x10,add(read(memory,p+0x10),mul(read(memory,p+0x70),read(memory,clock))))
    dt=read(memory,clock)
    step=add(mul(vy,dt),mul(mul(mul(bits(0.5),acceleration),dt),dt))
    put(memory,p+0x14,add(read(memory,p+0x14),step))
    put(memory,p+0x74,add(vy,mul(acceleration,read(memory,clock))))
    if floating(read(memory,p+0x7C)) < floating(read(memory,p+0x14)):
        put(memory,p+0x14,read(memory,p+0x7C))
        magnitude=read(memory,p+0x74)&0x7FFFFFFF
        put(memory,p+0x70,mul(read(memory,p+0x70),read(memory,damp_x)))
        put(memory,p+0x74,mul(magnitude,read(memory,damp_y)))
    return memory


def cases():
    for pattern,alias,phase in itertools.product(range(8),range(19),(0,8)):
        memory,args=fixture(pattern,alias)
        yield memory,args,phase
    for special,offset,phase in itertools.product((0x7FC12345,0xFFC54321,0x7F800000,0xFF800000,
            0x80000000,0x00800000,0x00000001), (0x10,0x14,0x70,0x74,0x78,0x7C), (0,8)):
        memory,args=fixture(5); put(memory,args[0]+offset,special)
        yield memory,args,phase


class MotionOracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,args,[],phase,entry,connected)
        self.io=[]

    def execute(self,word):
        if word>>26==17 and (word>>21)&31==16 and word&63==5:
            self.f[(word>>6)&31]=self.f[(word>>11)&31]&0x7FFFFFFF
        else: super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction: self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording: self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        if target!=source.ENTRY: raise ValueError('Child motion has no helpers after fabsf intrinsic')
        self.forwarded=self.r[4]


def state(m):
    return point.state(m),m.io,m.condition
