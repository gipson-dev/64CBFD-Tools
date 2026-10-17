"""Independent ordered byte/word reset semantics and emitted leaf execution."""
import itertools

from tools.experiments import game_overlay_defaults as source
from tools.tests import game_view_point_projection_oracle as point

put, read, STACK = point.put, point.read, point.STACK
NAMES = tuple(dict.fromkeys(v[0][1] for v in source.BINDINGS.values()))
ANCHORS = {n:int(n[2:],16) for n in NAMES}
MODE, COLOR, DURATION, COUNTER, KIND, ACTIVE, ENABLED, SCALE, PROJECTED, CONSTANT, SPEED = NAMES
MASK = 0xFFFFFFFF


def reference(initial, channel, anchors=ANCHORS):
    memory, events = dict(initial), []
    def get(name, offset=0, size=4):
        at = (anchors[name]+offset)&MASK
        value = read(memory, at, size)
        events.append(('R',at,size,value))
        return value
    def store(name, offset, value, size=4):
        at = (anchors[name]+offset)&MASK
        value &= (1 << (size*8))-1
        put(memory,at,value,size)
        events.append(('W',at,size,value))
    if get(MODE,size=1):
        for i in range(3):
            store(COLOR,channel*3+i,0,1)
        store(DURATION,channel*4,25)
        store(COUNTER,channel*4,0)
        store(KIND,channel,0,1)
        store(ACTIVE,channel,0,1)
    else:
        store(ENABLED,channel,1,1)
        store(SCALE,channel*4,0x3F800000)
        store(PROJECTED,channel*8,0)
        store(PROJECTED,channel*8+4,0)
        store(SPEED,channel*4,get(CONSTANT))
    return memory, events


def fixture(channel=0, flag=0, constant=0xBB83126F, anchors=ANCHORS, seed=0):
    memory = {STACK+i:(i*17+seed+0xA5)&255 for i in range(-0x300,0x120)}
    offsets = {MODE:(0,), COLOR:tuple(channel*3+i for i in range(3)),
        DURATION:(channel*4,), COUNTER:(channel*4,), KIND:(channel,), ACTIVE:(channel,),
        ENABLED:(channel,), SCALE:(channel*4,), PROJECTED:(channel*8,channel*8+4),
        CONSTANT:(0,), SPEED:(channel*4,)}
    for name, values in offsets.items():
        for offset in values:
            for i in range(-16,24):
                at = (anchors[name]+offset+i)&MASK
                memory.setdefault(at,(i*13+seed+0xA5)&255)
    put(memory,anchors[CONSTANT],constant)
    put(memory,anchors[MODE],flag,1)
    return memory


def corpus(anchors=ANCHORS):
    for channel, flag, constant, phase in itertools.product((0,1,2,3,-1,0x10001,0x7FFFFFFF,-0x80000000),
            (0,1,2,255), (0xBB83126F,0x80000000,0x7FC12345,0x7F800000,0x3F800000), (0,8)):
        yield fixture(channel,flag,constant,anchors), channel&MASK, phase


class ResetOracle(point.PointProjectionOracle):
    def __init__(self, words, memory, channel=0, phase=0, entry=source.ENTRY, connected=None):
        self.io = []
        super().__init__(words,memory,(channel,0,0,0),[],phase,entry,connected)

    def get(self, address, size):
        value = super().get(address,size)
        if self.own_instruction:
            self.io.append(('R',address,size,value))
        return value

    def put(self, address, value, size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:
            self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self, target):
        if target != source.ENTRY:
            raise ValueError('Unexpected reset callback')
        args = self.arguments(1)
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))

    def hook(self, target):
        raise ValueError('Reset must execute its actual emitted body')
