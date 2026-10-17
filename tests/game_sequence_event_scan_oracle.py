"""Independent six-query scan reference with explicit mutable provider contracts."""
import itertools

from tools.experiments import game_sequence_event_scan as source
from tools.tests import game_sequence_state_reset_oracle as reset

put, read, signed, STACK = reset.put, reset.read, reset.signed, reset.STACK
MASK = 0xFFFFFFFF
QUERY, COLOR = 0x15023BB0, 0x1517EE40
COUNTS, RECORDS, COLORS, RESULT, OUTPUT = 0x800C363A, 0x800C3688, 0x80084110, 0x800C3C8E, 0x800C35B0
FLAGS = (0x800C3C99, 0x800C3C9C, 0x800C35AA, 0x800C35A9)
KEYS = (30,14,104,68,119,1)
DATA, EVENTS = 0x60000, 0x70000
VALUES = (0,1,-1,-32768,32767,65535,65536,0x7FFFFFFF,-0x80000000,-65537)


def half(value): return (value ^ 32768) - 32768


def public(memory): return {a:v for a,v in memory.items() if not STACK-0x300 <= a < STACK+0x100}


def fixture(slot=0,count=3,present=63,nulls=0,pattern=0,mode=0,color_index=1):
    m = {STACK+i:0xA5 for i in range(-0x300,0x100)}
    for base,size in ((0x800C3500,0x900),(COLORS-384,768),(DATA,8*64),(EVENTS,8*6*16)):
        m.update({base+i:0xA5 for i in range(size)})
    for i in range(-128,128):
        for j in range(3): put(m,COLORS+i*3+j,(i*17+j*31+9)&255,1)
    put(m,COUNTS+slot,count,1)
    for i in range(8):
        put(m,RECORDS+slot*120+i*4,0 if nulls>>i&1 else DATA+i*64)
        for j in range(6):
            event=EVENTS+(i*6+j)*16
            put(m,event+5,color_index & 255,1); put(m,event+6,(1,0,-1,256)[(pattern+i)%4]&65535,2)
    return m,(slot,),dict(present=present,pattern=pattern,mode=mode)


def cases(native=False):
    for slot,count,present,nulls,pattern,mode in itertools.product((0,1),(0,1,3),(0,1,16,32,63),(0,2),(0,3,8),(0,1,2,4,8,16,31)):
        yield fixture(slot,count,present,nulls,pattern,mode)
    for slot,pattern in itertools.product((0,1),range(len(VALUES))):
        yield fixture(slot,4,63,0,pattern)
    if not native:
        for index in (-128,-1,127): yield fixture(color_index=index)
        yield fixture(count=8,nulls=255)


def answer(config,index,ordinal):
    value = VALUES[(config['pattern']+index*3+ordinal) % len(VALUES)] & MASK
    present = bool(config['present']>>ordinal&1)
    # Multi-record fixtures include missing events after earlier successes.
    if index&1 and config['pattern']&1: present = not present
    return (EVENTS+(index*6+ordinal)*16 if present else 0), value


def effects(memory,slot,index,ordinal,mode,color=False):
    writes=[]; fired=[]
    if not color and index == 0 and ordinal == 0:
        if mode&1: writes.append((COUNTS+slot,1,1)); fired.append('live-count')
        if mode&2: writes.append((RECORDS+slot*120,DATA+7*64,4)); fired.append('cached-commands')
        if mode&4: writes.append((RECORDS+slot*120+4,DATA+6*64,4)); fired.append('next-record')
    if not color and ordinal == 5 and mode&8:
        writes.extend(((RESULT,0xFEDC,2),(FLAGS[0],0,1))); fired.append('late-shared-state')
    if color and mode&16:
        writes.extend(((RESULT,0x8001,2),(COUNTS+slot,1,1))); fired.append('color-live-state')
    for at,value,width in writes: put(memory,at,value,width)
    return writes,fired


class Reference:
    def __init__(self,memory,args,config):
        self.memory=dict(memory); self.slot=args[0]; self.config=config; self.calls=[]; self.script=[]; self.fired=[]

    def call(self,target,packet,ordinal=None):
        m=self.memory; self.calls.append((target,packet))
        if target == QUERY:
            index=packet[2]; event,value=answer(self.config,index,ordinal)
            writes,fired=effects(m,self.slot,index,ordinal,self.config['mode'])
        else:
            event=value=0; writes,fired=effects(m,self.slot,0,0,self.config['mode'],True)
        self.fired.extend(fired); self.script.append((target,packet,event,value,writes))
        return event,value

    def run(self):
        m=self.memory; slot=self.slot
        for at in FLAGS: put(m,at,0,1)
        put(m,RESULT,0,2); best=-1; index=0
        while index < read(m,COUNTS+slot,1):
            record=read(m,RECORDS+slot*120+index*4)
            if record:
                for ordinal,key in enumerate(KEYS):
                    event,value=self.call(QUERY,(record+24,5,index,0,1,key,int(ordinal==5),0,0,0,slot),ordinal)
                    if event:
                        if ordinal < 4: put(m,FLAGS[ordinal],1,1)
                        elif ordinal == 4: put(m,RESULT,value&65535,2)
                        elif best == -1 or signed(value)<best:
                            best=signed(value); color=COLORS+((read(m,event+5,1)^128)-128)*3
                            self.call(COLOR,tuple(read(m,color+i,1) for i in range(3))+(0,int(half(read(m,event+6,2))==1),0))
            index+=1
        put(m,OUTPUT+slot*4,read(m,RESULT,2)); return self


def load_signed_byte(machine,word):
    machine.own_instruction=True
    try:
        offset=((word&65535)^32768)-32768
        value=machine.get((machine.r[word>>21&31]+offset)&MASK,1)
        machine.r[word>>16&31]=((value^128)-128)&MASK
        machine.r[0]=0
    finally: machine.own_instruction=False


class EventOracle(reset.machine.InitializeOracle):
    def __init__(self,words,memory,args,config,phase=0,entry=source.ENTRY,helpers=None):
        super().__init__(words,memory,args,helpers or {},phase,entry=entry)
        self.slot=args[0]; self.config=config; self.fired=[]; self.raw_packets=[]; self.snapshots=[]; self.cuts=[]

    def execute(self,word):
        if word>>26 == 32: load_signed_byte(self,word)
        else: super().execute(word)

    def record_call(self,target):
        arity={QUERY:11,COLOR:6,source.ENTRY:1}[target]; raw=self.arguments(arity); self.raw_packets.append((target,raw))
        packet=raw[:3]+(0,)+raw[4:] if target==QUERY else raw
        self.calls.append((target,packet)); self.events.append(('CALL',target,packet))
        self.cuts.append((target,tuple(self.r[r] for r in (*range(16,24),28,29,30)),
            read(self.memory,self.r[29]+0x68),read(self.memory,self.r[29]+0x74)))

    def hook(self,target):
        packet=self.raw_packets[-1][1]; value=0
        if target==QUERY:
            if read(self.memory,packet[3]) != 0: raise ValueError('Output pointer was not cleared before each query')
            ordinal=KEYS.index(packet[5]); event,value=answer(self.config,packet[2],ordinal)
            self.put(packet[3],event,4)
            _,fired=effects(self.memory,self.slot,packet[2],ordinal,self.config['mode'])
        elif target==COLOR:
            _,fired=effects(self.memory,self.slot,0,0,self.config['mode'],True)
        else: raise ValueError('Unexpected event scan provider')
        self.fired.extend(fired); self.snapshots.append(public(self.memory))
        for i in range(4): self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25): self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]; self.r[2]=value
