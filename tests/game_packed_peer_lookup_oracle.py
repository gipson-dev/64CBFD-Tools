"""Independent numeric packed-row lookup reference and bounded fixtures."""
from dataclasses import dataclass

from tools.tests import test_game_route_record_copy_match as core

COUNT,TABLE,ARENA=0x80087380,0x800D23C0,0x90000
STACK,put,read=core.STACK,core.put,core.read


@dataclass(frozen=True)
class Case:
    arguments:tuple
    rows:tuple


def key(arguments):return (((arguments[0]&65535)<<12)+(arguments[1]&65535))&65535


def expected(case):
    wanted=key(case.arguments);group=case.arguments[2]&65535
    for row in case.rows:
        hits=[i for i,entry in enumerate(row) if entry==wanted]
        if not hits:continue
        peers=[entry&4095 for i,entry in enumerate(row) if i!=hits[0] and entry//4096==group]
        return peers[0] if peers else -1
    return -1


def cases():
    yield Case((1,1,2),())
    yield Case((1,1,2),((),))
    yield Case((1,1,2),((0x1001,), (0x1001,0x2002)))
    yield Case((1,1,1),((0x1001,),))
    yield Case((1,1,1),((0x1001,0x1001),))
    for group in range(16):
        for value in (0,1,15,255,4095,4096,0x7FFF,0x8000,0xFFFF):
            packed=((group<<12)+value)&65535
            for peer in (0,group,group^1,16,65535):
                yield Case((group,value,peer),((),(packed,0x0005,0x1006,0x2007,0xF008)))
    for first in range(8):
        for second in range(8):
            row=[0xE001]*8;row[first]=0x1001
            if second!=first:row[second]=0x2002
            yield Case((1,1,2),(tuple(row),))
    seed=0x51F38A27
    def random():
        nonlocal seed
        seed=(seed*1664525+1013904223)&0xFFFFFFFF;return seed
    for n in range(1024):
        args=(random(),random(),random());rows=[]
        for i in range(random()%5):
            row=[random()&65535 for _ in range(random()%9)]
            if row and n&1:row[n%len(row)]=key(args)
            if len(row)>1 and n&2:row[(n+1)%len(row)]=((args[2]&15)<<12)|(n&4095)
            rows.append(tuple(row))
        yield Case(args,tuple(rows))
    for high in (0,0x10000,0x7FFF0000,0x80000000,0xFFFF0000):
        for args in ((1,1,2),(1,0x1002,1),(0xFFFF,0xFFFF,0xFFFF)):
            yield Case(tuple(high|v for v in args),((0x1001,0x2002,0x1003,0xF001),))


def fixture(case,phase=0,count_address=COUNT,table_address=TABLE,arena=ARENA):
    m={STACK+i:((i*17+0xA5)&255) for i in range(-64,128)}
    for i in range(max(1,len(case.rows))*24):m[(arena+i)&0xFFFFFFFF]=0xA5
    put(m,count_address,len(case.rows),4);put(m,table_address,arena,4)
    for i,row in enumerate(case.rows):
        put(m,arena+i*24+2,len(row),2)
        for j,entry in enumerate(row):put(m,arena+i*24+8+j*2,entry,2)
    return m,tuple(v&0xFFFFFFFF for v in case.arguments)


def public(memory):return {a:v for a,v in memory.items() if not STACK-64<=a<STACK+128}


class LookupModel(core.CopyModel):
    def record_call(self,target):self.caller_args.append((target,*self.r[4:7]))
    def hook(self,target):raise AssertionError('Unexpected packed-peer external call: %X'%target)
