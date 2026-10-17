"""Typed fields, live padding, bounded allocator effects and actual SDK copy."""
import itertools
import struct

from tools.experiments import game_overlay_fade_packet as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.game_animation_timeline_oracle import signed

put, read, STACK = point.put, point.read, point.STACK
EVENT, RNG, MASK = 0x20020, 0x150ADA20, 0xFFFFFFFF


def half(value):
    return ((value&65535)^32768)-32768


def provider_arguments(args):
    return (half(args[4])&MASK,MASK,0x39,3,1,0,8,args[6]&255,args[7]&MASK)


def payload(args, padding):
    rate = (args[3]&255)//half(args[4])
    return bytes([*(x&255 for x in args[:4]),args[5]&255,padding,rate>>8,rate&255])


def fixture(args, phase=0, seed=0):
    memory = {STACK+i:(i*17+seed*31+0xA5)&255 for i in range(-0x300,0x120)}
    memory.update({EVENT+i:(i*13+seed*31+0xA5)&255 for i in range(-32,160)})
    for i in range(4,8):
        put(memory,STACK+phase+i*4,args[i]&MASK)
    return memory


def provider_effects(memory, sp, mode):
    for i in range(4):
        put(memory,sp+i*4,0xB5000000+i)
    if mode == 1:
        put(memory,sp+0x39,0x5A,1)
    elif mode == 2:
        put(memory,sp+0x4C,0xAABBCCDD)
        put(memory,sp+0x50,0)


def reference(initial, args, phase=0, outcome=1, mode=0):
    memory = dict(initial)
    sp = STACK+phase-64
    put(memory,sp+0x2C,0xDEAD0000)
    for i in range(4):
        put(memory,STACK+phase+i*4,args[i]&MASK)
    calls = []
    if half(args[4]) <= 0:
        return memory,calls
    raw = payload(args,memory[sp+0x39])
    for i in (0,1,2,3,4,6,7):
        put(memory,sp+0x34+i,raw[i],1)
    for offset,value in ((0x10,1),(0x14,0),(0x18,8),(0x1C,args[6]&255),(0x20,args[7])):
        put(memory,sp+offset,value&MASK)
    calls.append((source.PROVIDER,provider_arguments(args)))
    provider_effects(memory,sp,mode)
    if outcome:
        destination = EVENT+(outcome-1)+0x28
        calls.append((source.MEMCPY,(destination,sp+0x34,8)))
        for i in range(8):
            put(memory,destination+i,read(memory,sp+0x34+i,1),1)
    return memory,calls


def cases():
    for duration,alpha,channel,outcome,mode,phase in itertools.product(
            (0,1,2,15,32767,65535,0x8000,0x10001,0x80000001),(0,1,199,255,511),
            (0,255,0x10002),(0,1,2),(0,1,2),(0,8)):
        args = (0x123456CC,0xABCDEF45,0x102030FF,alpha,duration,channel,0x10081,0x8765ABCD)
        yield fixture(args,phase),args,phase,outcome,mode


class GuestBreak(Exception):
    pass


class FadeOracle(point.PointProjectionOracle):
    def __init__(self, words, memory, args, memcpy_words, phase=0, outcome=1, mode=0,
            entry=source.ENTRY, connected=None, provider=source.PROVIDER, memcpy=source.MEMCPY, random=(0,0)):
        code = dict(zip(range(memcpy,memcpy+44,4),memcpy_words))
        code.update(connected or {})
        self.io,self.copies,self.packets,self.forwarded = [],[],[],[]
        self.outcome,self.mode,self.provider,self.memcpy = outcome,mode,provider,memcpy
        self.random,self.random_index = random,0
        super().__init__(words,memory,args,[],phase,entry,code)
        self.mode = mode

    def execute(self, word):
        op,rs,rt,rd,fn = word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
        if op == 0 and fn in (26,27):
            a,b = (signed(self.r[rs]),signed(self.r[rt])) if fn == 26 else (self.r[rs],self.r[rt])
            if not b or a == -0x80000000 and b == -1:
                raise GuestBreak('Outside bounded valid division domain')
            quotient = abs(a)//abs(b)*(-1 if (a<0) != (b<0) else 1)
            self.lo,self.hi = quotient&MASK,(a-quotient*b)&MASK
        elif op == 0 and fn == 16:
            self.r[rd] = self.hi
        elif op == 0 and fn == 13:
            raise GuestBreak(word)
        else:
            super().execute(word)

    def get(self, address, size):
        value = super().get(address,size)
        if self.own_instruction:
            self.io.append(('R',address,size,value))
        return value

    def put(self, address, value, size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:
            self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def arguments_at_call(self, count):
        return tuple(self.r[4:4+min(4,count)])+tuple(read(self.memory,self.r[29]+i*4) for i in range(4,count))

    def record_call(self, target):
        if target == source.ENTRY:
            self.forwarded.append(self.arguments_at_call(8))
            return
        if target == self.provider:
            args = self.arguments_at_call(9)
            self.packets.append(bytes(read(self.memory,self.r[29]+0x34+i,1) for i in range(8)))
        elif target == self.memcpy:
            args = tuple(self.r[4:7])
            self.copies.append(bytes(read(self.memory,args[1]+i,1) for i in range(args[2])))
        elif target == RNG:
            args = ()
        else:
            raise ValueError('Unexpected fade helper '+hex(target))
        self.calls.append((target,args))

    def hook(self, target):
        if target == self.provider:
            provider_effects(self.memory,self.r[29],self.mode)
            result = EVENT+self.outcome-1 if self.outcome else 0
        elif target == RNG:
            result = self.random[self.random_index%2]
            self.random_index += 1
        else:
            raise ValueError('The SDK copy must execute its actual eleven words')
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = result&MASK


def memcpy_words(rom):
    return list(struct.unpack_from('>11I',rom,0x22EC0))
