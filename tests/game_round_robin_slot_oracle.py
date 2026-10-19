"""Numeric circular-search reference; sparse guest indices are not native arrays."""
from dataclasses import dataclass

from tools.experiments import game_round_robin_slot_candidates as source
from tools.tests import test_game_route_record_copy_match as core

STATE,COUNT,MASK,ACTORS=0x800D23B0,0x8008FD8C,0x800D18A0,0x800CC2D0
CONTEXT,NESTED=0x30000,0x50000
STACK,put,read=core.STACK,core.put,core.read
DEFAULT=dict(D_800D23B0=STATE,D_8008FD8C=COUNT,D_800D18A0=MASK,D_800CC2D0=ACTORS)


def signed8(value):return (value+128)%256-128


@dataclass(frozen=True)
class Case:
    cursor:int
    count:int
    mask:int
    pattern:int


def stage(index,pattern):
    if pattern<4:return (0,1,3,7)[pattern]
    if pattern<8:return 7 if index%4==pattern-4 else 0
    return ((index*17+pattern*13)^(index>>2))&7


def native_cases():
    for count in range(1,27):
        for cursor in (-1,0,count-1,25):
            for pattern in range(8):
                for mask in (0,0xFFFF,0xA55A):yield Case(cursor,count,mask,pattern)
    for count in (0,-128,-1):
        for pattern in range(8):yield Case(-1,count,0xA55A,pattern)


def cases():
    yield from native_cases()
    for byte in range(256):
        yield Case(signed8(byte),(-128,-1,0,1,26,127)[byte%6],(byte*257)&65535,byte%16)
        yield Case(127 if byte&1 else -1,signed8(byte),0xFFFF,3 if byte&2 else 0)


def fixture(case,phase=0,anchors=None,context=CONTEXT,nested=NESTED):
    anchors=DEFAULT if anchors is None else anchors
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,128)}
    put(m,anchors['D_800D23B0'],context,4);put(m,anchors['D_8008FD8C'],case.count,1)
    put(m,anchors['D_800D18A0'],case.mask,2)
    for i in range(-4,5):m[context+0x1702+i]=0xA5
    put(m,context+0x1702,case.cursor,1)
    for index in range(-128,128):
        actor=(anchors['D_800CC2D0']+index*0x32C)&0xFFFFFFFF;value=stage(index,case.pattern)
        node=nested+(index+128)*256
        put(m,actor,0x12340000+(index&255) if value&1 else 0,4)
        put(m,actor+0x31C,node if value&2 else 0,4)
        put(m,node+0x84,(0x80 if index&1 else 0xFF) if value&4 else 0,1)
    return m


def reference(memory,anchors=None):
    anchors=DEFAULT if anchors is None else anchors;m=memory.copy()
    context=read(m,anchors['D_800D23B0'],4);count=signed8(read(m,anchors['D_8008FD8C'],1))
    cursor=signed8(read(m,context+0x1702,1));selected=-1
    for attempt in range(max(1,count)):
        cursor=signed8(cursor+1)
        if cursor>=count:cursor=0
        actor=(anchors['D_800CC2D0']+cursor*0x32C)&0xFFFFFFFF
        if read(m,actor,4)==0:continue
        node=read(m,actor+0x31C,4)
        if node==0 or read(m,node+0x84,1)==0:continue
        if read(m,anchors['D_800D18A0'],2)&(1<<(cursor&31)):continue
        selected=cursor;break
    put(m,context+0x1702,cursor,1);return selected&0xFFFFFFFF,m


def public(memory):return {a:v for a,v in memory.items() if not STACK-256<=a<STACK+128}


class SlotModel(core.CopyModel):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY):
        super().__init__(words,memory,(),phase=phase,entry=entry)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected slot-selector callee')
        self.caller_args.append(())

    def hook(self,target):raise ValueError('Slot selector unexpectedly called a provider')
