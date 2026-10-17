"""Actual descriptor factory and SDK copies with one bounded allocator boundary."""
import itertools
import struct

from tools.experiments import game_fixed_transition_constructor as source
from tools.tests import game_view_point_projection_oracle as point

put,read,STACK = point.put,point.read,point.STACK
EVENT = 0x20020
DESCRIPTOR_PADDING = (0x11,0x42,0x43,0x45,0x46,0x47)
PAYLOAD_PADDING = (1,2,3)


def descriptor(memory,at,id,mode):
    values = ((0,0xC3960000,4),(4,0x42900000,4),(8,0x40F00000,4),(12,0x40F00000,4),
        (0x10,0xC1,1),(0x12,id&65535,2),(0x14,0x31,2),(0x16,1,2),(0x18,255,2),(0x1A,8,1),
        *((i,255,1) for i in range(0x1B,0x24)),(0x24,0,4),(0x28,0x200004,4),(0x2C,0x9F0601,4),
        (0x30,23,4),(0x34,68,4),(0x38,128,4),(0x3C,32,4),(0x40,0,1),(0x41,10,1),
        (0x44,mode&255,1),(0x48,0x3F800000,4),(0x4C,0x3F800000,4),(0x50,0,4),(0x54,0,4))
    for offset,value,size in values:
        put(memory,at+offset,value,size)


def payload(memory,at):
    for offset,value,size in ((0,0,1),(4,0,4),(8,0xC3960000,4),(12,0,4)):
        put(memory,at+offset,value,size)


def fixture(mode=0,seed=0,mode_address=source.MODE):
    memory = {STACK+i:(i*17+seed*31+0xA5)&255 for i in range(-0x300,0x120)}
    memory.update({EVENT+i:(i*13+seed*31+0xA5)&255 for i in range(-32,192)})
    memory.update({mode_address+i:0xA5 for i in range(-8,12)})
    put(memory,mode_address,mode&0xFFFFFFFF)
    return memory


def effects(memory,constructor_sp,factory_sp,mode,mode_address):
    for i in range(4):
        put(memory,factory_sp+i*4,0xB5000000+i)
    if mode==1:
        for i,offset in enumerate(DESCRIPTOR_PADDING):
            put(memory,constructor_sp+0x40+offset,0x5A+i,1)
    elif mode==2:
        for i,offset in enumerate(PAYLOAD_PADDING):
            put(memory,constructor_sp+0x30+offset,0xA0+i,1)
        put(memory,mode_address,0xAABBCCDD)


def reference(initial,args,phase=0,outcome=1,mode=0,entry=source.ENTRY,factory=source.FACTORY,
        allocator=source.ALLOCATOR,memcpy=source.MEMCPY,mode_address=source.MODE,return_address=0xDEAD0000):
    memory = dict(initial)
    sp = STACK+phase-152; inner=sp-56
    put(memory,sp+0x24,return_address)
    for i,value in enumerate(args):
        put(memory,STACK+phase+i*4,value&0xFFFFFFFF)
    descriptor(memory,sp+0x40,args[0],read(memory,mode_address))
    payload(memory,sp+0x30)
    for offset,value in ((0x10,16),(0x14,args[1]&255),(0x18,args[2])):
        put(memory,sp+offset,value&0xFFFFFFFF)
    calls = [(factory,(sp+0x40,12,0,0,16,args[1]&255,args[2]&0xFFFFFFFF))]
    put(memory,inner+0x20,0x5A000010)
    put(memory,inner+0x24,entry+0x15C)
    put(memory,inner+0x3C,12)
    put(memory,inner+0x10,args[1]&255)
    put(memory,inner+0x14,1)
    calls.append((allocator,(0x57,args[2]&0xFFFFFFFF,128,1,args[1]&255,1)))
    effects(memory,sp,inner,mode,mode_address)
    if outcome:
        event=EVENT+outcome-1
        put(memory,inner+0x34,event)
        calls.append((memcpy,(event+0x10,sp+0x40,88)))
        for i in range(88):
            put(memory,event+0x10+i,read(memory,sp+0x40+i,1),1)
        put(memory,event+0x68,12,1)
        calls.append((memcpy,(event+0x70,sp+0x30,16)))
        for i in range(16):
            put(memory,event+0x70+i,read(memory,sp+0x30+i,1),1)
    return memory,calls


def cases():
    for id,slot,context,view,outcome,mode,phase in itertools.product(
            (0,1,0x7FFF,0x8000,0xFFFF,0xABCD8001),(0,255,0x10081),
            (0,0x8765ABCD,0xFFFFFFFF),(0,255,0x10002,0x80000003),(0,1,2),(0,1,2),(0,8)):
        args=(id,slot,context)
        yield fixture(view),args,phase,outcome,mode


class ConstructorOracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,factory_words,memcpy_words,phase=0,outcome=1,mode=0,
            entry=source.ENTRY,constructor=source.ENTRY,factory=source.FACTORY,allocator=source.ALLOCATOR,
            memcpy=source.MEMCPY,mode_address=source.MODE,connected=None):
        code=dict(zip(range(factory,factory+216,4),factory_words))
        code.update(dict(zip(range(memcpy,memcpy+44,4),memcpy_words)))
        code.update(connected or {})
        super().__init__(words,memory,args,[],phase,entry,code)
        self.constructor,self.factory,self.allocator,self.memcpy=constructor,factory,allocator,memcpy
        self.outcome,self.effect_mode,self.mode_address=outcome,mode,mode_address
        self.io,self.forwarded,self.descriptors,self.payloads,self.copies=[],[],[],[],[]
        self.constructor_sp=None

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:
            self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:
            self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def arguments_at_call(self,count):
        return tuple(self.r[4:4+min(4,count)])+tuple(read(self.memory,self.r[29]+i*4) for i in range(4,count))

    def record_call(self,target):
        if target==self.constructor:
            self.forwarded.append(self.arguments_at_call(3))
            return
        if target==self.factory:
            args=self.arguments_at_call(7)
            self.constructor_sp=args[0]-0x40
            self.descriptors.append(bytes(read(self.memory,args[0]+i,1) for i in range(88)))
            self.payloads.append(bytes(read(self.memory,self.constructor_sp+0x30+i,1) for i in range(16)))
        elif target==self.allocator:
            args=self.arguments_at_call(6)
        elif target==self.memcpy:
            args=tuple(self.r[4:7])
            self.copies.append(bytes(read(self.memory,args[1]+i,1) for i in range(args[2])))
        else:
            raise ValueError('Unexpected constructor helper '+hex(target))
        self.calls.append((target,args))

    def hook(self,target):
        if target!=self.allocator or self.constructor_sp is None:
            raise ValueError('Factory and SDK copies must execute actual instructions')
        effects(self.memory,self.constructor_sp,self.r[29],self.effect_mode,self.mode_address)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=EVENT+self.outcome-1 if self.outcome else 0


def helper_words(rom):
    return list(struct.unpack_from('>54I',rom,0x18293C)),list(struct.unpack_from('>11I',rom,0x22EC0))
