"""Public transition/burst contract with real factory, byte copies and tag leaves.

RNG, direction output, sine and lower allocation are explicitly scripted. This
does not qualify private stack bytes, portable C padding, real heap or gameplay.
"""
import itertools
import struct
from tools.experiments import game_transition_completion_burst as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import game_fixed_transition_oracle as constructor
from tools.tests.game_sequence_event_scan_oracle import load_signed_byte

bits, floating, add, mul = point.bits, point.floating, point.add, point.mul
put, read, STACK = point.put, point.read, point.STACK
RECORD, EVENTS, ALT_TAG = 0x30020, 0x40020, source.TAG - 12
PADDING = constructor.DESCRIPTOR_PADDING
MASK = 0xFFFFFFFF


def random_word(seed, index):
    return (seed + index * 1664525 + 1013904223) & MASK


def random_float(seed, index):
    return bits((0., 0.25, 0.5, 0.75, 1.)[(seed + index) % 5])


def sine(word):
    # A deterministic finite return validates the call ABI, not libm's accuracy.
    return mul(word, bits(0.125))


def success(index, pattern):
    return pattern == 1 or pattern == 2 and index % 2 == 0


def mutate(memory, mode, iteration):
    if iteration == 0 and mode == 1:
        for at, value in ((RECORD+0x10, bits(123.)), (RECORD+0x14, bits(-67.)),
                (RECORD+0x74, bits(0.625)), (RECORD+0x78, bits(7.)), (RECORD+0x7C, bits(-3.))):
            put(memory, at, value)
        put(memory, RECORD+1, 201, 1)
        put(memory, RECORD+12, 253, 1)
    elif iteration == 0 and mode == 2:
        put(memory, source.MODE, 0xABCDEF80)
        put(memory, source.TIMESTEP, bits(-8.))
        put(memory, source.TAG_TABLE+8, ALT_TAG)


def fixture(flags=1, progress=0., timestep=1., seed=0):
    memory = {STACK+i:(i*17+seed*31+0xA5)&255 for i in range(-0x500, 0x120)}
    for base, size in ((RECORD-16, 176), (EVENTS-16, 5*160+32), (source.MODE-8, 20),
            (source.TIMESTEP-8, 20), (source.TAG_TABLE-8, 32)):
        memory.update({base+i:(i*13+seed*7+0xA5)&255 for i in range(size)})
    for at, value, size in ((RECORD+1, 129, 1), (RECORD+12, 255, 1), (RECORD+0x70, flags, 1),
            (RECORD+0x10, bits(-12.25), 4), (RECORD+0x14, bits(44.5), 4),
            (RECORD+0x74, bits(progress), 4), (RECORD+0x78, bits(-300.), 4),
            (RECORD+0x7C, bits(450.), 4), (source.TIMESTEP, bits(timestep), 4),
            (source.MODE, 0xABCD0123, 4), (source.TAG_TABLE+8, source.TAG, 4)):
        put(memory, at, value, size)
    for i, byte in enumerate(source.POOL_BYTES):
        put(memory, source.POOL+i, byte, 1)
    return memory


def descriptor(x, y, scale, tag, id, flags, duration, view):
    result = {i:0xA5 for i in range(88)}
    constructor.descriptor(result, 0, id, view)
    for at, value, size in ((0,x,4), (4,y,4), (8,scale,4), (12,scale,4), (16,tag,1),
            (20,flags,2), (22,12,2), (24,21,2), (26,0,1), (30,duration,1)):
        put(result, at, value, size)
    return bytes(result[i] for i in range(88))


def initialized(data):
    return tuple(None if i in PADDING else b for i,b in enumerate(data))


def public(memory, pattern, mode, count):
    omitted = {EVENTS+n*160+16+i for n in range(count) if success(n,pattern) for i in PADDING} if mode != 3 else set()
    return {a:b for a,b in memory.items() if not STACK-0x500 <= a < STACK+0x120 and a not in omitted}


def reference(initial, seed=0, pattern=1, mode=0):
    memory, calls = dict(initial), []
    rng = floats = count = 0
    def integer():
        nonlocal rng
        value = random_word(seed,rng); rng += 1; calls.append(('random', value)); return value
    def real():
        nonlocal floats
        value = random_float(seed,floats); floats += 1; calls.append(('float', value)); return value
    if read(memory,RECORD+0x70,1)&1:
        progress = add(read(memory,RECORD+0x74),mul(0x3E428F5D,read(memory,source.TIMESTEP)))
        put(memory,RECORD+0x74,progress)
        if floating(progress) >= 1.:
            put(memory,RECORD+0x74,bits(1.))
            put(memory,RECORD+0x70,read(memory,RECORD+0x70,1)&254,1)
            count = (integer()&3)+2
            x,y = read(memory,RECORD+16),read(memory,RECORD+20)
            floor = add(y,bits(15.)); view = read(memory,source.MODE)&255
            for iteration in range(count):
                duration = integer()%101+155
                target = read(memory,source.TAG_TABLE+8)
                calls.append(('tag',target)); tag = 29 if target == source.TAG else 117
                angle = integer()%65-160
                speed = add(mul(real(),bits(2.)),bits(2.5))
                calls.append(('direction',angle&MASK,speed))
                vx,vy = mul(speed,bits(-0.25)),mul(speed,bits(0.5))
                mutate(memory,mode,iteration)
                acceleration = add(mul(real(),0x3EAA7EFA),0x3ECED917)
                scale = add(mul(real(),0x3FE51EB8),0x3FD99999)
                id = integer()%26+30
                flag0,flag1 = (2 if integer()&1 else 0),(4 if integer()&1 else 0)
                desc = descriptor(x,y,scale,tag,id,flag0|flag1|0x39,duration,view)
                slot,context = read(memory,RECORD+12,1),read(memory,RECORD+1,1)
                calls.append(('factory',13,0,0,16,slot,context,initialized(desc)))
                calls.append(('allocator',0x57,context,128,1,slot,1))
                if success(iteration,pattern):
                    event = EVENTS+iteration*160
                    if mode == 3:
                        desc = bytearray(desc)
                        for i,at in enumerate(PADDING): desc[at] = 0x60+i+iteration
                    for i,b in enumerate(desc): put(memory,event+16+i,b,1)
                    put(memory,event+104,13,1)
                    calls.append(('copy',88))
                    payload = {}
                    for i,value in enumerate((vx,vy,acceleration,floor)): put(payload,i*4,value)
                    for i in range(16): put(memory,event+112+i,payload[i],1)
                    calls.append(('copy',16))
            progress = read(memory,RECORD+0x74)
        put(memory,RECORD+16,add(read(memory,RECORD+0x78),mul(progress,read(memory,RECORD+0x7C))))
        sine_arg = mul(read(memory,RECORD+0x74),0x40490FDB)
        calls.append(('sine',sine_arg))
        put(memory,RECORD+20,add(mul(sine(sine_arg),bits(-17.5)),bits(72.)))
    return public(memory,pattern,mode,count),calls,count


def cases():
    for flags, progress, timestep, seed, pattern, mode, phase in itertools.product(
            (0,1,128,255), (-0.5,0.9,1.), (-1.,1.), range(4), range(3), range(4), (0,8)):
        yield fixture(flags,progress,timestep,seed),seed,pattern,mode,phase


class CallerJoin(Exception):
    pass


class CompletionOracle(point.PointProjectionOracle):
    def __init__(self,words,memory,rom,seed=0,pattern=1,mode=0,phase=0,
            entry=source.ENTRY,connected=None):
        code = dict(connected or {})
        for helper_entry,offset,count in ((source.FACTORY,0x18293C,54),(source.MEMCPY,0x22EC0,11),
                (source.TAG,0x20636C,3),(ALT_TAG,0x206360,3)):
            values = struct.unpack_from('>%dI'%count,rom,offset)
            code.update({helper_entry+i*4:w for i,w in enumerate(values)})
        super().__init__(words,memory,(RECORD,),[],phase,entry,code)
        self.seed,self.pattern,self.mode = seed,pattern,mode
        self.rng=self.floats=0
        self.active_descriptor=None; self.hi=0

    def execute(self,word):
        if word==0xFFFFFFFF:
            raise CallerJoin
        op,fn,rs,rt,rd = word>>26,word&63,word>>21&31,word>>16&31,word>>11&31
        if op==32:
            load_signed_byte(self,word)
        elif op==0 and fn==27:
            a,b=self.r[rs],self.r[rt]
            if not b: raise AssertionError('Unexpected zero divisor')
            self.lo,self.hi=a//b,a%b
        elif op==0 and fn==16:
            self.r[rd]=self.hi
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            self.forwarded=self.r[4]
            return
        if target in (source.RANDOM,source.RANDOM_FLOAT): return
        if target in (source.TAG,ALT_TAG):
            self.calls.append(('tag',target)); return
        if target==source.DIRECTION:
            self.calls.append(('direction',self.r[4],self.r[5]))
            assert self.r[7]==self.r[6]+4
        elif target==source.FACTORY:
            args=self.arguments(7); self.active_descriptor=args[0]
            data=bytes(read(self.memory,args[0]+i,1) for i in range(88))
            self.calls.append(('factory',*args[1:],initialized(data)))
        elif target==source.ALLOCATOR:
            self.calls.append(('allocator',*self.arguments(6)))
        elif target==source.MEMCPY:
            self.calls.append(('copy',self.r[6]))
        elif target==source.SINE:
            self.calls.append(('sine',self.f[12]))
        else: raise ValueError('Unexpected completion helper '+hex(target))

    def hook(self,target):
        result=None; value=0xA5000002
        if target==source.RANDOM:
            value=random_word(self.seed,self.rng); self.rng+=1; self.calls.append(('random',value))
        elif target==source.RANDOM_FLOAT:
            result=random_float(self.seed,self.floats); self.floats+=1; self.calls.append(('float',result))
        elif target==source.DIRECTION:
            put(self.memory,self.r[6],mul(self.r[5],bits(-0.25)))
            put(self.memory,self.r[7],mul(self.r[5],bits(0.5)))
            mutate(self.memory,self.mode,(self.rng-3)//5)
        elif target==source.ALLOCATOR:
            iteration=sum(c[0]=='allocator' for c in self.calls)-1
            value=EVENTS+iteration*160 if success(iteration,self.pattern) else 0
            if self.mode==3:
                for i,at in enumerate(PADDING): put(self.memory,self.active_descriptor+at,0x60+i+iteration,1)
        elif target==source.SINE:
            result=sine(self.f[12])
        else: raise ValueError('Actual factory/copies/tags must execute')
        for i in range(4): put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in (1,2,3,*range(4,16),24,25): self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.lo,self.hi=0x12345678,0x87654321
        self.r[2]=value
        if result is not None: self.f[0]=result
