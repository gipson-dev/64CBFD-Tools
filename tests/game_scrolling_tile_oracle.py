"""Live coordinate reads, two exact SDK words each, aliases and bounded faults."""
from tools.experiments import game_scrolling_tile_windows as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.game_animation_timeline_oracle import signed

put,read,STACK = point.put,point.read,point.STACK
CURSOR = 0x20020
NAMES = ('D_80088890','D_80088894','D_80088898','D_8008889C')
ANCHORS = {name:int(name[2:],16) for name in NAMES}


def fixture(values,alias=0,anchors=None):
    anchors = anchors or ANCHORS
    cursor = CURSOR if not alias else anchors[NAMES[0]]+(-8,0,8,16,-16,24)[alias-1]
    memory = {STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x120)}
    for base in (*anchors.values(),cursor):
        memory.update({base+i:(i*13+0xA5)&255 for i in range(-32,64)})
    for name,value in zip(NAMES,values):
        put(memory,anchors[name],value&0xFFFFFFFF)
    return memory,cursor


def reference(initial,cursor,anchors=None):
    memory,events = dict(initial),[]
    anchors = anchors or ANCHORS
    for tile in (0,1):
        coordinates = []
        for name in NAMES[tile*2:tile*2+2]:
            at = anchors[name]; value=read(memory,at)
            events.append(('R',at,4,value))
            coordinates.append((signed(value)>>7)&4095)
        high = 0xF2000000+(coordinates[0]<<12)+coordinates[1]
        low = (tile<<24)+0x47E47E
        for offset,value in ((0,high),(4,low)):
            put(memory,cursor+tile*8+offset,value)
            events.append(('W',cursor+tile*8+offset,4,value))
    return memory,events,cursor+16


def cases():
    boundaries = (0,1,127,128,129,-1,-127,-128,-129,0x7FFFFFFF,-0x80000000,0x7FFF80,-0x7FFF80)
    values = [tuple(boundaries[(i+j*3)%len(boundaries)] for j in range(4)) for i in range(len(boundaries))]
    values += [tuple(((i+1)*(j+3)*1664525+1013904223*(j+1))&0xFFFFFFFF for j in range(4)) for i in range(128)]
    for raw in values:
        for alias in range(7):
            memory,cursor = fixture(raw,alias)
            for phase in (0,8):
                yield memory,cursor,phase


class TileOracle(point.PointProjectionOracle):
    def __init__(self,words,memory,cursor,phase=0,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,(cursor,),[],phase,entry,connected)
        self.io = []

    def get(self,address,size):
        value = super().get(address,size)
        if self.own_instruction:
            self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:
            self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        if target!=source.ENTRY:
            raise ValueError('Unexpected scrolling-tile call')
        self.calls.append((target,(self.r[4],)))

    def hook(self,target):
        raise ValueError('Scrolling tile body must execute its actual words')
