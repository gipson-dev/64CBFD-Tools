"""Independent row dispatch reference with explicit bounded handler contracts."""
from dataclasses import dataclass

from tools.experiments import game_packed_row_dispatch_candidates as source
from tools.tests import test_game_route_record_copy_match as core

COUNT,TABLE=0x80087380,0x800D23C0
BANKS=(0x90000,0x94000)
H2,H3,CLEAR=0x15114B94,0x1503DDD0,0x1508EDBC
STACK,put,read=core.STACK,core.put,core.read
DEFAULT={'D_80087380':COUNT,'D_800D23C0':TABLE,'func_15114B94':H2,'func_1503DDD0':H3,'func_1508EDBC':CLEAR}


@dataclass(frozen=True)
class Case:
    arguments:tuple
    rows:tuple
    mode:int=0


def key(case):return (((case.arguments[0]&65535)<<12)+(case.arguments[1]&65535))&65535


def matched_row(case):
    return next((i for i,row in enumerate(case.rows) if key(case) in row),None)


def first_handler(case):
    row=matched_row(case)
    return None if row is None else next((i for i,v in enumerate(case.rows[row]) if v>>12 in (2,3)),None)


def cases():
    for mode in range(6):
        for rows in ((),((),),((0x1001,),),((0x1001,),(0x1001,0x2002)),
                ((0x1001,0x2002,0x3003),),((),(0x2002,0x1001,0x3003))):
            yield Case((1,1),rows,mode)
    for group in range(16):
        for value in (0,1,15,255,4095,4096,0x7FFF,0x8000,0xFFFF):
            packed=((group<<12)+value)&65535
            for mode in range(6):yield Case((group,value),((),(packed,0x2005,0xF006,0x3007)),mode)
    for length in range(1,9):
        for where in range(length):
            row=[((2+(i&1))<<12)|(i+17) for i in range(length)];row[where]=0x1001
            for mode in range(6):yield Case((1,1),(tuple(row),),mode)
    seed=0x8A719B23
    def random():
        nonlocal seed
        seed=(seed*1664525+1013904223)&0xFFFFFFFF;return seed
    for n in range(128):
        arguments=(random(),random());rows=[]
        for i in range(random()%5):
            row=[random()&65535 for _ in range(random()%9)]
            if row and n&1:row[n%len(row)]=(((arguments[0]&65535)<<12)+(arguments[1]&65535))&65535
            rows.append(tuple(row))
        for mode in range(6):yield Case(arguments,tuple(rows),mode)
    for high in (0x10000,0x7FFF0000,0x80000000,0xFFFF0000):
        for mode in range(6):yield Case((high|1,high|1),((0x1001,0x2002,0x3003),),mode)


def fixture(case,phase=0,anchors=None,banks=BANKS):
    anchors=DEFAULT if anchors is None else anchors
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,128)}
    for bank,base in enumerate(banks):
        for i in range(96):m[base+i]=0xA5
        for row in range(4):
            values=case.rows[row] if row<len(case.rows) else ()
            put(m,base+row*24,0x1234+bank*16+row,2)
            put(m,base+row*24+2,len(values),2);put(m,base+row*24+4,0xABC00000+bank*256+row,4)
            for i in range(8):
                value=values[i] if i<len(values) else ((2+i%3)<<12)|(0x400+row*16+i)
                if bank and i<len(values):value=(value&0xF000)|((value+0x40)&4095)
                put(m,base+row*24+8+i*2,value,2)
    put(m,anchors['D_80087380'],len(case.rows),4);put(m,anchors['D_800D23C0'],banks[0],4)
    return m,tuple(v&0xFFFFFFFF for v in case.arguments)


def provider(memory,target,args,case,store,number,anchors=None,banks=BANKS):
    anchors=DEFAULT if anchors is None else anchors;count,table=anchors['D_80087380'],anchors['D_800D23C0']
    if target==CLEAR:
        index=args[0]
        if index<read(memory,count,4):
            for offset,size in ((2,2),(4,4),(0,2)):store(read(memory,table,4)+index*24+offset,0,size)
        return
    if target not in (H2,H3):raise ValueError(hex(target))
    if number!=1 or case.mode==0:return
    row=matched_row(case);index=first_handler(case);current=read(memory,table,4)
    if case.mode in (1,3,4):store(table,banks[1],4);current=banks[1]
    if case.mode==2:store(current+row*24+2,0,2)
    elif case.mode==3:store(count,0,4)
    elif case.mode==4:store(current+row*24+2,8,2);store(count,row,4)
    elif case.mode==5:
        for i in range(index+1,len(case.rows[row])):
            store(current+row*24+8+i*2,((3 if i&1 else 1)<<12)|(0x500+row*16+i),2)


def reference(memory,case,anchors=None,banks=BANKS):
    anchors=DEFAULT if anchors is None else anchors;m=memory.copy();calls=[];handlers=0
    count,table=anchors['D_80087380'],anchors['D_800D23C0']
    def store(at,value,size):put(m,at,value,size)
    def invoke(target,arg):
        nonlocal handlers
        calls.append((target,arg))
        if target!=CLEAR:handlers+=1
        provider(m,target,(arg,),case,store,handlers,anchors,banks)
    total=read(m,count,4);base=read(m,table,4) if total else 0
    for row in range(total):
        length=read(m,base+row*24+2,2)
        values=[read(m,base+row*24+8+i*2,2) for i in range(length)]
        if key(case) not in values:continue
        index=0;limit=length
        while index<limit:
            value=read(m,read(m,table,4)+row*24+8+index*2,2);kind=value>>12
            if kind in (2,3):
                invoke(H2 if kind==2 else H3,value&4095)
                limit=read(m,read(m,table,4)+row*24+2,2)
            index+=1
        invoke(CLEAR,row);break
    return m,calls


def public(memory):return {a:v for a,v in memory.items() if not STACK-256<=a<STACK+128}


def observation(memory,calls,anchors=None,banks=BANKS):
    anchors=DEFAULT if anchors is None else anchors
    result=[read(memory,anchors['D_80087380'],4),banks.index(read(memory,anchors['D_800D23C0'],4)),
        sum(target!=CLEAR for target,arg in calls),len(calls)]
    for base in banks:
        for row in range(4):
            result.extend((read(memory,base+row*24,2),read(memory,base+row*24+2,2),read(memory,base+row*24+4,4)))
            result.extend(read(memory,base+row*24+8+i*2,2) for i in range(8))
    trace=[]
    for target,arg in calls:trace.extend((1 if target==H2 else 2 if target==H3 else 3,arg))
    return result+trace[:20]+[0]*max(0,20-len(trace))


class DispatchModel(core.CopyModel):
    def __init__(self,words,memory,args,case,phase=0,entry=source.ENTRY,anchors=None,banks=BANKS,clear_words=None):
        super().__init__(words,memory,args,phase=phase,entry=entry)
        self.case,self.anchors,self.banks=case,DEFAULT if anchors is None else anchors,banks;self.handlers=0
        self.targets={self.anchors[name]:value for name,value in (('func_15114B94',H2),('func_1503DDD0',H3),('func_1508EDBC',CLEAR))}
        if clear_words is not None:self.code.update(zip(range(CLEAR,CLEAR+len(clear_words)*4,4),clear_words))

    def record_call(self,target):
        if target==source.ENTRY:self.caller_args.append(tuple(self.r[4:6]));return
        canonical=self.targets[target];args=(self.r[4],);self.calls.append((canonical,*args));self.events.append(('CALL',target,args))

    def hook(self,target):
        canonical=self.targets[target];self.in_hook=True
        try:
            if canonical!=CLEAR:self.handlers+=1
            provider(self.memory,canonical,(self.r[4],),self.case,self.put,self.handlers,self.anchors,self.banks)
            for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)];self.lo=0xDEAD0000+self.handlers
        finally:self.in_hook=False
