"""Bounded matrix provider, exact float32 reference, and real projection/draw code."""
import math
import struct

from tools.experiments import game_projected_packet_draw as source
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.game_animation_timeline_oracle import bits, floating, signed

STACK, put, read = edge.STACK, edge.put, edge.read
PACKET, OUTPUT, VIEWS, MATRIX, MATRIX_CALL = 0x30000, 0x60000, 0x50000, 0x800D2CA8, 0x150A7A00
NEAR = 0x800D9B20


def rounded(x):
    return floating(bits(x))


def half(x):
    return ((x+32768)&65535)-32768


def frame_values(index):
    return (17.25+index*13.5, -23.125+index*4.75, 311.5-index*17.25, 199.25+index*31.5)


def viewport_values(index):
    return (-32768, -16384) if index == 0 else (32767, 32767)


def fixture(coordinates=(-32768, 0, 32767), transformed=(17.25, -91.5, 100., 2.), frame=0, view=0, alias=False):
    assert not STACK-2048 <= OUTPUT < STACK+256
    memory = {STACK+i: (i*17+0xA5)&255 for i in range(-2048, 256)}
    packet = OUTPUT if alias else PACKET
    for base, size in ((PACKET, 48), (OUTPUT, 128), (VIEWS, 0x300), (MATRIX, 128)):
        memory.update({base+i: 0xA5 for i in range(size)})
    for i, value in enumerate(coordinates):
        put(memory, packet+i*2, value, 2)
    for i in range(2):
        for offset,value in zip((0xC,0x10,0x34,0x38), frame_values(i)):
            put(memory, VIEWS+i*0x180+offset, bits(value))
        for v in (0,3):
            scale,translation = viewport_values(v)
            put(memory, VIEWS+i*0x180+v*16+0x44, scale, 2)
            put(memory, VIEWS+i*0x180+v*16+0x4C, translation, 2)
    for a,v in ((source.FRAME_INDEX,frame),(source.VIEW_BASE,VIEWS),(source.VIEW_INDEX,view),(NEAR,bits(1.))):
        put(memory,a,v,1 if a == source.VIEW_INDEX else 4)
    return memory, (OUTPUT,packet), tuple(map(bits,transformed))


def mutate(memory):
    put(memory, source.FRAME_INDEX, read(memory,source.FRAME_INDEX)^1)
    put(memory, source.VIEW_INDEX, 3 if read(memory,source.VIEW_INDEX,1)==0 else 0, 1)


def project_reference(initial, output_addresses, transformed, maximum=4000., mode=0):
    memory = dict(initial)
    for a,b in zip(output_addresses,transformed):
        put(memory,a,b)
    if mode:
        mutate(memory)
    w = floating(read(memory,output_addresses[3]))
    if maximum <= w or w <= floating(read(memory,NEAR)):
        return memory,0
    reciprocal = rounded(1./w)
    view = (read(memory,source.VIEW_BASE)+read(memory,source.FRAME_INDEX)*0x180)&0xFFFFFFFF
    scaleX,scaleY,translateX,translateY = [floating(read(memory,view+i)) for i in (0xC,0x10,0x34,0x38)]
    x,y = [floating(read(memory,a)) for a in output_addresses[:2]]
    x = rounded(rounded(rounded(rounded(scaleX+5.)*x)*reciprocal)+translateX)
    y = rounded(translateY-rounded(rounded(rounded(scaleY+5.)*y)*reciprocal))
    put(memory,output_addresses[0],bits(x))
    put(memory,output_addresses[1],bits(y))
    return memory,1


def draw_reference(initial,args,transformed,phase=0,mode=0):
    private = STACK+phase-0x48
    outputs = (private+0x44,private+0x40,private+0x3C,private+0x38)
    memory,result = project_reference(initial,outputs,transformed,mode=mode)
    calls = [('matrix', MATRIX+read(initial,source.FRAME_INDEX)*64,
        *[bits(float(half(read(initial,args[1]+i*2,2)))) for i in range(3)], *outputs)]
    if not result:
        return memory,args[0],calls
    put(memory,args[0],0xE7000000)
    put(memory,args[0]+4,0)
    put(memory,args[0]+8,0xEE000000)
    address = (read(memory,source.VIEW_BASE)+read(memory,source.FRAME_INDEX)*0x180+read(memory,source.VIEW_INDEX,1)*16)&0xFFFFFFFF
    depth,w = floating(read(memory,outputs[2])),floating(read(memory,outputs[3]))
    scale,translation = half(read(memory,address+0x44,2)),half(read(memory,address+0x4C,2))
    value = rounded(rounded(float(translation)+rounded(rounded(depth/w)*float(scale)))*32.)
    put(memory,args[0]+12,(math.trunc(value)<<16)&0xFFFFFFFF)
    calls.append(('draw',args[0]+16,args[1],read(memory,outputs[0]),read(memory,outputs[1]),
        read(memory,outputs[3]),1,0,0,0))
    return memory,args[0]+24,calls


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-2048<=a<STACK+256}


class ProjectionOracle(edge.EdgeOracle):
    def __init__(self,words,memory,args,transformed,mode=0,bindings=None,**kwargs):
        self.transformed = transformed
        self.bindings = bindings or {}
        super().__init__(words,memory,args,mode=mode,entry=kwargs.pop('entry',source.ENTRY),**kwargs)

    def record_call(self,target):
        target = self.bindings.get(target,target)
        if target == source.PROJECT:
            return
        if target == MATRIX_CALL:
            self.calls.append(('matrix',*self.arguments(8)))
        elif target == source.DRAW:
            self.calls.append(('draw',*self.arguments(9)))
        else:
            raise AssertionError(('unexpected projection provider',hex(target)))

    def hook(self,target):
        target = self.bindings.get(target,target)
        if target == MATRIX_CALL:
            arguments = self.arguments(8)
            for a,b in zip(arguments[4:],self.transformed):
                self.put(a,b,4)
            if self.mode:
                mutate(self.memory)
            result = 0xA5000123
        else:
            assert target == source.DRAW
            result = self.r[4]+8
        for r in (*range(1,16),24,25):
            self.r[r] = 0xA5000000+r
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = result
