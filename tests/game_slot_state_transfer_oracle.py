"""Independent transfer reference with explicit, bounded helper providers."""
from dataclasses import dataclass,replace

from tools.experiments import game_slot_state_transfer_candidates as source
from tools.tests import test_game_route_record_copy_match as core

MASK,LOCK,LEVEL,TABLE,ACTORS,MODE,ROOT,COUNT=0x800D18A0,0x800D18A2,0x800D18A4,0x800D23B0,0x800CC2D0,0x800BE9F0,0x800D2E48,0x8008FD94
GET,SET,SWAP,LOOKUP,FINISH=0x150859AC,0x15085710,0x15062800,0x1509B570,0x15128774
BANKS=(0x90000,0x94000);STATES=(0x98000,0x98400,0x98800);SCRIPT,CHILD=0xA0000,0xA4000
ARITY={GET:2,SET:3,SWAP:2,LOOKUP:1,FINISH:2}
IDS={GET:1,SET:2,SWAP:3,LOOKUP:4,FINISH:5}
FIELDS=(0x9C,0x39C,0x3DC,0xEB0,0x16C0)
STACK,put,read=core.STACK,core.put,core.read


def u32(v):return v&0xFFFFFFFF
def s32(v):return (v&0x7FFFFFFF)-(v&0x80000000)
def s16(v):return (v&0x7FFF)-(v&0x8000)
def actor(slot):return u32(ACTORS+u32(slot*812))
def address(base,offset):return u32(base+offset)


@dataclass(frozen=True)
class Case:
    destination:int=3
    source:int=5
    level:int=51
    locked:int=0
    mask:int=0xA55A
    flags:int=0xFFFFFFFF
    mode:int=63
    tag:int=103
    kind:int=23
    owner:int=1
    lookup:int=1
    half:int=0x8123
    counter:int=127
    mutate:int=0


def cases():
    for value in range(256):yield Case(level=value,mutate=value&1)
    for value in range(256):
        for mutate in (0,1):yield Case(tag=value,kind=value*137&255,counter=value,half=value*257,mutate=mutate)
    for destination in range(16):
        for locked in (0,65535,1<<destination,1<<((destination+1)&15)):
            for mutate in (0,1):yield Case(destination=destination,source=(destination+5)&15,locked=locked,
                mask=(0,65535,0x5555,0xAAAA)[destination&3],mode=0,mutate=mutate)
    for owner in (-1,0,1,15):
        for lookup in (0,1):
            for mutate in (0,1):yield Case(owner=owner,lookup=lookup,mutate=mutate)
    for slot in range(16):
        for mutate in (0,1):yield Case(destination=slot,source=slot,mutate=mutate)
    for flags in (0,1,0x80000000):
        for mutate in (0,1):yield Case(flags=flags,mutate=mutate)


def fixture(case,phase=0,bank=None):
    banks=(BANKS[0] if bank is None else bank,BANKS[1]);m={}
    for base,length in ((STACK-0x300,0x500),*( (b,0x1800) for b in banks),
            *((s,0x200) for s in STATES),(SCRIPT,0x3000),(CHILD,16)):
        m.update({u32(base+i):0xA5 for i in range(length)})
    for slot in {case.destination,case.source}:
        m.update({address(actor(slot),i):0xA5 for i in range(812)})
    for slot in range(256):put(m,actor(slot)+0x3B,slot*7+29,1)
    for number,base in enumerate(banks):
        put(m,address(base,0x18),case.flags,4)
        for field in FIELDS:
            for slot in {case.destination,case.source}:
                value=(0x12000000+number*0x10000+field+u32(slot*17))&0xFFFFFFFF
                if field==0xEB0:value=case.owner
                put(m,address(base,field+u32(slot*4)),value,4)
        if case.owner>=0:put(m,address(base,0xF70+case.owner*4),0xA5A5A5A5,4)
    for at,value,size in ((MASK,case.mask,2),(LOCK,case.locked,2),(TABLE,banks[0],4),
            (MODE,case.mode,4),(ROOT,0x12345678,4),(COUNT,case.counter,1),
            (address(LEVEL,case.destination),case.level,1),
            (actor(case.destination)+0x31C,STATES[0],4),(actor(case.destination)+0x318,CHILD,4),
            (actor(case.destination)+0x13C,case.tag,1),(STATES[0]+0x1AA,case.half,2),
            (actor((case.tag-100)&255)+0x3B,case.kind,1)):
        put(m,u32(at),value,size)
    return m,(u32(case.destination),u32(case.source))


def provider(memory,target,args,case,store):
    if target==GET:
        if case.mutate:
            for at,value,size in ((MASK,read(memory,MASK,2)^0x55AA,2),(LOCK,read(memory,LOCK,2)^0x0F0F,2),
                    (address(LEVEL,case.destination),0,1),(TABLE,BANKS[1],4)):
                store(at,value,size)
        return 0xCAFE0000|(args[0]&65535)
    if target==SET:return 0xDEADC0DE
    if target==SWAP:
        if case.mutate:
            store(args[1]+0x31C,STATES[1],4);store(STATES[1]+0x1AA,0x5555,2)
        return 0xDEADBEEF
    if target==LOOKUP:
        if case.mutate:
            for at,value,size in ((actor(case.destination)+0x13C,0,1),
                    (actor((case.tag-100)&255)+0x3B,case.kind^0x80,1),
                    (actor(case.destination)+0x31C,STATES[2],4),(STATES[2]+0x1AA,0x6666,2)):
                store(at,value,size)
        return SCRIPT if case.lookup else 0
    if target==FINISH:
        if case.mutate:store(COUNT,127,1)
        return 0xDEADC0DE
    raise ValueError(hex(target))


def reference(memory,args,case):
    m=memory.copy();calls=[];captures=[]
    def store(at,value,size):put(m,u32(at),value,size)
    def invoke(target,*arguments):
        arguments=tuple(u32(v) for v in arguments);calls.append((target,*arguments))
        captures.append((target,read(m,MASK,2),read(m,LOCK,2),read(m,address(LEVEL,args[0]),1)))
        return provider(m,target,arguments,case,store)
    destination,original_source=args
    destination_bit=1<<(destination&31)
    if read(m,address(LEVEL,destination),1)<51 or read(m,LOCK,2)&destination_bit:return m,calls,captures
    inverse=u32(~destination_bit);source_bit=1<<(original_source&31)
    store(MASK,read(m,MASK,2)&inverse,2);store(LOCK,read(m,LOCK,2)|destination_bit,2)
    store(MASK,read(m,MASK,2)|source_bit,2)
    score=invoke(GET,s16(original_source),3)
    invoke(SET,s16(destination),2,score);invoke(SET,s16(original_source),2,0)
    def table():return read(m,TABLE,4)
    if read(m,address(table(),0x18),4):
        store(address(table(),0x18),read(m,address(table(),0x18),4)&inverse,4)
        store(address(table(),0x18),read(m,address(table(),0x18),4)|source_bit,4)
    for field in (0x9C,0x39C,0x3DC,0xEB0):
        base=table()
        if address(base,field):
            store(address(base,field+u32(destination*4)),read(m,address(base,field+u32(original_source*4)),4),4)
            if field==0xEB0:
                index=s32(read(m,address(table(),field+u32(destination*4)),4))
                if index>=0:store(address(table(),0xF70+u32(index*4)),destination,4)
    base=table();store(address(base,0x16C0+u32(destination*4)),read(m,address(base,0x16C0+u32(original_source*4)),4),4)
    output=actor(destination);old_half=s16(read(m,read(m,output+0x31C,4)+0x1AA,2))
    invoke(SWAP,actor(original_source),output)
    if read(m,MODE,4)==63 and read(m,output+0x13C,1)>=100:
        linked=(read(m,output+0x13C,1)-100)&255
        script=invoke(LOOKUP,read(m,ROOT,4))
        if script:
            offset=read(m,actor(linked)+0x3B,1)-20
            delta=s32(u32(output-ACTORS));identity=(abs(delta)//812)*(-1 if delta<0 else 1)
            store(address(script,0x24B8+offset*4),identity|0x2000,4)
            store(address(script,0x24DC+offset*4),identity,4)
    store(read(m,output+0x31C,4)+0x84,0,1);store(output+0x125,90,1)
    store(read(m,output+0x31C,4)+0x1AA,old_half,2);store(read(m,output+0x31C,4)+0x1AF,64,1)
    invoke(FINISH,read(m,output+0x318,4),output);store(COUNT,read(m,COUNT,1)+1,1)
    return m,calls,captures


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x200}


class TransferModel(core.CopyModel):
    def __init__(self,words,memory,args,case,phase=0,entry=source.ENTRY):
        super().__init__(words,memory,args,phase=phase,entry=entry)
        self.case,self.arguments=case,args;self.captures,self.private=[],[]

    def execute(self,word):
        if word>>26==0 and word&63==39:
            self.r[word>>11&31]=u32(~(self.r[word>>21&31]|self.r[word>>16&31]));self.r[0]=0
        else:super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:self.caller_args.append(tuple(self.r[4:6]));return
        args=tuple(self.r[4:4+ARITY[target]]);self.calls.append((target,*args));self.events.append(('CALL',target,args))
        self.captures.append((target,read(self.memory,MASK,2),read(self.memory,LOCK,2),
            read(self.memory,address(LEVEL,self.arguments[0]),1)))
        if target==GET:
            self.private.append(tuple(read(self.memory,self.r[29]+offset,4) for offset in (0x1C,0x20,0x24,0x50,0x54)))

    def hook(self,target):
        self.in_hook=True
        try:
            args=tuple(self.r[4:4+ARITY[target]])
            result=provider(self.memory,target,args,self.case,self.put)
            for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)];self.lo=0xDEAD0000
            self.r[2]=u32(result)
        finally:self.in_hook=False


def observation(memory,calls,captures,case):
    values=[read(memory,MASK,2),read(memory,LOCK,2),read(memory,address(LEVEL,case.destination),1),
        int(read(memory,TABLE,4)==BANKS[1]),read(memory,COUNT,1),len(calls)]
    for base in BANKS:
        values.append(read(memory,base+0x18,4))
        for field in FIELDS:
            for slot in (case.destination,case.source):values.append(read(memory,base+field+slot*4,4))
        values.append(read(memory,base+0xF70+max(0,case.owner)*4,4))
    output=actor(case.destination);state=read(memory,output+0x31C,4)
    values.extend((read(memory,output+0x125,1),read(memory,output+0x13C,1),STATES.index(state)))
    for at in STATES:values.extend((read(memory,at+0x1AA,2),read(memory,at+0x84,1),read(memory,at+0x1AF,1)))
    linked=(case.tag-100)&255;offset=read(memory,actor(linked)+0x3B,1)-20
    values.extend((read(memory,SCRIPT+0x24B8+offset*4,4),read(memory,SCRIPT+0x24DC+offset*4,4)))
    values.extend(captures[0][1:] if captures else (0,0,0))
    rows=[]
    for target,*args in calls:
        if target==SWAP:args=[u32(s32(u32(a-ACTORS))//812) for a in args]
        elif target==FINISH:args=[0xF0000010 if args[0]==CHILD else args[0],u32(s32(u32(args[1]-ACTORS))//812)]
        rows.extend((IDS[target],*args,*([0]*(3-len(args)))))
    values.extend(rows+[0]*(24-len(rows)))
    return tuple(u32(v) for v in values)
