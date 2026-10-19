"""Ordered release reference; finite conversions and explicit guest alias backing."""
from dataclasses import dataclass
import math
import struct

from tools.experiments import game_record_release_candidates as source
from tools.tests import test_game_route_record_copy_match as core

STATE,ACTORS=0x800D23B0,0x800CC2D0
BANKS=(0x50000,0x54000)
SIZE,ACTOR_WORDS=0x1600,26*0x32C//4
STACK,put,read=core.STACK,core.put,core.read
DEFAULT={'D_800D23B0':STATE,'D_800CC2D0':ACTORS}
ARRAYS=(0xEB0,0xF70,0xFF0,0x1070,0x10F0,0x11F4,0x12F4,0x1374,0x13F4,0x1474)


def signed(v):return v if v<0x80000000 else v-0x100000000
def floating(v):return struct.unpack('>f',struct.pack('>I',v&0xFFFFFFFF))[0]
def bits(v):return struct.unpack('>I',struct.pack('>f',v))[0]
def add50(v):return bits(floating(v)+50.0)


def truncate(v):
    value=floating(v)
    if not math.isfinite(value) or not -0x80000000<=math.trunc(value)<0x80000000:
        raise ValueError('Outside qualified finite signed conversion')
    return math.trunc(value)&0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    slot:int=0
    record:int=0
    mode:int=1
    flags:int=0
    next_state:int=7
    coords:tuple=(0,0,0)
    seed:int=0
    layout:int=0
    null:bool=False


def native_cases():
    positions=((0.,0.,0.),(1.75,-49.5,-1.75),(-123.875,-0.75,123.875),(0.,-50.5,0.),
        (-2147483648.,2147483520.,2147483520.),(0.125,-0.125,-0.125))
    n=0
    for slot in (0,1,7,25):
        for record in (-1,0,3,31):
            for mode in (-0x80000000,-1,0,1,2,0x7FFFFFFF):
                for flags in (0,1,2,3,0x80000000):
                    yield Case(slot,record,mode,flags,(-1,0,7,-0x80000000)[n%4],tuple(map(bits,positions[n%6])),n&255);n+=1
    values=(0x00000000,0x80000000,0x00000001,0x80000001,0x007FFFFF,0x807FFFFF,
        bits(1.75),bits(-1.75),bits(-49.5),bits(-50.5),bits(-0.75),bits(8388607.5),0x4EFFFFFF,0xCF000000)
    for axis in range(3):
        for value in values:
            coords=[bits(1.75),bits(-49.5),bits(-1.75)];coords[axis]=value
            yield Case(3,1,coords=tuple(coords),seed=n&255);n+=1
    for bit in range(32):
        for mode in (0,1):yield Case(0,2,mode,1<<bit,coords=tuple(map(bits,(1.75,-49.5,-1.75))),seed=bit)
    for slot in (-0x80000000,-1,0,25,0x40000000,0x7FFFFFFF):
        for mode in (-0x80000000,-1,0,1,2,0x7FFFFFFF):yield Case(slot,0,mode,coords=(0x7FC00000,0x7F800000,0xFF800000),null=True)
    for slot in (0,1,25):
        for mode in (-1,0,1):yield Case(slot,-1,mode,coords=(0x7FC00000,0x7F800000,0xFF800000))
    for mode,flags in ((-1,0),(0,0),(1,2),(2,0)):
        yield Case(mode=mode,flags=flags,coords=(0x7FC00000,0x7F800000,0xFF800000))
    for mode in (-1,0,1,2):yield Case(209,0,mode,coords=tuple(map(bits,(1.75,-49.5,-1.75))))


def cases():
    yield from native_cases()
    positions=((1.75,-49.5,-1.75),(123.875,-0.75,2.75),(0.,3.5,7.99),(1000.5,100.25,5.125))
    for layout in range(1,9):
        for slot in (0,1,7):
            for record in (0,1,7):
                for coords in positions:
                    coords=list(map(bits,coords))
                    if layout==2:coords[0]=bits(float(BANKS[1]))
                    elif layout==3:coords[1]=bits(float(BANKS[1])-50.)
                    elif layout==4:coords[2]=bits(float(BANKS[1]))
                    yield Case(slot,record,coords=tuple(coords),layout=layout)
    for slot in (-1,0x40000000,0x80000000,0xC0000000,0x7FFFFFFF):
        for mode in (-1,0,1):yield Case(slot,0,mode,coords=tuple(map(bits,(1.75,-49.5,-1.75))))
    for record in (0x40000000,0x7FFFFFFF):
        for mode in (-1,0,1):yield Case(0,record,mode,coords=tuple(map(bits,(1.75,-49.5,-1.75))))


def word_pattern(index,seed,bank):return ((index*0x1020305)^(seed*0x01010101)^(bank*0x11223344)^0xA53C719B)&0xFFFFFFFF


def fixture(case,phase=0,anchors=None,banks=BANKS):
    anchors=DEFAULT if anchors is None else anchors;state,actors=anchors['D_800D23B0'],anchors['D_800CC2D0']
    slot,record=case.slot&0xFFFFFFFF,case.record&0xFFFFFFFF;record_offset=(record*4)&0xFFFFFFFF
    actor=(actors+slot*0x32C)&0xFFFFFFFF;context=banks[0]
    if case.layout in (1,2,3,4):context=(state-(0x12F4,0x1374,0x13F4,0x1474)[case.layout-1]-record_offset)&0xFFFFFFFF
    elif case.layout in (5,6,7,8):
        actor_offset,output_offset=((0x18,0x12F4),(0x1C,0x12F4),(0x18,0x1374),(0x1C,0x13F4))[case.layout-5]
        context=(actor+actor_offset-output_offset-record_offset)&0xFFFFFFFF
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,128)}
    contexts=list(dict.fromkeys((*banks,300,context)))
    for bank,base in enumerate(contexts):
        identity=bank if bank<2 else bank+1
        offsets={0,4,0xEAC}
        for offset in ARRAYS:
            offsets.update(offset+i*4 for i in range(32))
            offsets.add((offset+record_offset)&0xFFFFFFFF)
        offsets.add((0xEB0+slot*4)&0xFFFFFFFF)
        for offset in offsets:put(m,(base+offset)&0xFFFFFFFF,word_pattern(offset//4,case.seed,identity),4)
        put(m,(base+0xEAC)&0xFFFFFFFF,case.next_state,4)
        put(m,(base+0xEB0+slot*4)&0xFFFFFFFF,record,4)
        if signed(record)>=0:put(m,(base+0x11F4+record_offset)&0xFFFFFFFF,case.flags,4)
    for offset in range(0x10,0x34,4):
        logical=((slot*0x32C+offset)&0xFFFFFFFF)//4
        put(m,(actor+offset)&0xFFFFFFFF,word_pattern(logical,case.seed,2),4)
    coords=list(case.coords)
    if case.layout==2:coords[0]=bits(float(banks[1]))
    elif case.layout==3:coords[1]=bits(float(banks[1])-50.)
    elif case.layout==4:coords[2]=bits(float(banks[1]))
    for i,value in enumerate(coords):put(m,(actor+0x14+i*4)&0xFFFFFFFF,value,4)
    put(m,state,0 if case.null else context,4)
    return m,(slot,case.mode&0xFFFFFFFF),context,actor


def reference(memory,args,anchors=None,trace=None):
    anchors=DEFAULT if anchors is None else anchors;m=memory.copy();state,actors=anchors['D_800D23B0'],anchors['D_800CC2D0']
    slot,mode=args;initial=read(m,state,4)
    if initial==0:return 0,m
    selection=(initial+slot*4+0xEB0)&0xFFFFFFFF;record=signed(read(m,selection,4))
    if record<0:return 0,m
    if signed(mode)<0:return 1,m
    def store(at,value):
        put(m,at,value,4)
        if trace is not None:trace.append((at,4,value&0xFFFFFFFF))
    def destination(offset):return (read(m,state,4)+record*4+offset)&0xFFFFFFFF
    store(selection,0xFFFFFFFF)
    if read(m,destination(0x11F4),4)&2:return 0,m
    store(destination(0xF70),0xFFFFFFFF);store(destination(0x10F0),0xFFFFFFFF)
    next_state=read(m,(read(m,state,4)+0xEAC)&0xFFFFFFFF,4)
    if mode==1:
        store(destination(0x12F4),300);actor=(actors+slot*0x32C)&0xFFFFFFFF
        store(destination(0x1374),truncate(read(m,(actor+0x14)&0xFFFFFFFF,4)))
        store(destination(0x13F4),truncate(add50(read(m,(actor+0x18)&0xFFFFFFFF,4))))
        store(destination(0x1474),truncate(read(m,(actor+0x1C)&0xFFFFFFFF,4)));next_state=4
    store(destination(0x1070),next_state);return 0,m


def public(memory):return {a:v for a,v in memory.items() if not STACK-256<=a<STACK+128}


class ConversionBoundary(Exception):pass


class ReleaseModel(core.CopyModel):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY):
        super().__init__(words,memory,args,phase=phase,entry=entry)
        self.conversions=0;self.stop_conversion=None;self.conversion_word=None;self.requested=None

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            self.conversion_word=word
            if self.stop_conversion==self.conversions:raise ConversionBoundary()
            self.conversions+=1
        super().execute(word)

    def get(self,address,size):
        self.requested=('R',address,size);return super().get(address,size)

    def put(self,address,value,size):
        self.requested=('W',address,size);return super().put(address,value,size)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected record-release callee')
        self.caller_args.append(tuple(self.r[4:6]))

    def hook(self,target):raise ValueError('Record release unexpectedly called a provider')
