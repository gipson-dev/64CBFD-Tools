"""Independent ordered-store reference and explicit guest alias fixtures."""
from dataclasses import dataclass

from tools.experiments import game_parallel_array_reset_candidates as source
from tools.tests import test_game_route_record_copy_match as core

STATE,CONTEXT=0x800D23B0,0x40000
STACK,put,read=core.STACK,core.put,core.read
SIZE=0x1400
DEFAULT={'D_800D23B0':STATE}
OUTPUTS=((0xF70,0xFFFFFFFF),(0xFF0,0),(0x10F0,0xFFFFFFFF),(0x1070,1),(0x12F4,0))


def signed(value):return value if value<0x80000000 else value-0x100000000


@dataclass(frozen=True)
class Case:
    first:int
    second:int
    pattern:int=0
    mode:int=0
    redirected:int=0


def native_cases():
    for first in (-0x80000000,-1,0,1,2,7,16,48):
        for second in (-0x80000000,-1,0,1,2,7,16,32):
            for pattern in (0,1,7,127,128,255):yield Case(first,second,pattern)


def cases():
    yield from native_cases()
    for mode in range(1,5):
        for first in (0,2,7):
            for second in (0,1,2,4,8):
                for redirected in (0,1,2,4):
                    for pattern in (0,255):yield Case(first,second,pattern,mode,redirected)


def word_pattern(index,pattern):return ((index*0x1020305)^(pattern*0x01010101)^0xA53C719B)&0xFFFFFFFF


def fixture(case,phase=0,anchors=None,context=CONTEXT):
    anchors=DEFAULT if anchors is None else anchors;state=anchors['D_800D23B0']
    offsets={1:0xFF0,2:0x12F4,3:0xFF4,4:0x12F8}
    if case.mode:context=state-offsets[case.mode]
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,128)}
    for index in range(SIZE//4):put(m,context+index*4,word_pattern(index,case.pattern),4)
    put(m,context+0x10,case.first,4);put(m,context+0xEA4,case.second,4)
    put(m,state,context,4)
    if case.mode:put(m,0xEA4,case.redirected,4)
    return m,context


def reference(memory,anchors=None,trace=None):
    anchors=DEFAULT if anchors is None else anchors;m=memory.copy();state=anchors['D_800D23B0']
    initial=read(m,state,4);current=initial;index=0
    while index<signed(read(m,(current+0x10)&0xFFFFFFFF,4)):
        at=(initial+0xEB0+index*4)&0xFFFFFFFF;put(m,at,0xFFFFFFFF,4)
        if trace is not None:trace.append((at,4,0xFFFFFFFF))
        current=read(m,state,4);index+=1
        if index>256:raise ValueError('Unbounded reset reference fixture')
    index=0
    while index<signed(read(m,(current+0xEA4)&0xFFFFFFFF,4)):
        for offset,value in OUTPUTS:
            at=(initial+offset+index*4)&0xFFFFFFFF;put(m,at,value,4)
            if trace is not None:trace.append((at,4,value))
        current=read(m,state,4);index+=1
        if index>256:raise ValueError('Unbounded reset reference fixture')
    return m


def public(memory):return {a:v for a,v in memory.items() if not STACK-256<=a<STACK+128}


class ResetModel(core.CopyModel):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY):
        super().__init__(words,memory,(),phase=phase,entry=entry)
        self.requested=None

    def get(self,address,size):
        self.requested=('R',address,size);return super().get(address,size)

    def put(self,address,value,size):
        self.requested=('W',address,size);return super().put(address,value,size)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected reset callee')
        self.caller_args.append(())

    def hook(self,target):raise ValueError('Reset unexpectedly called a provider')
