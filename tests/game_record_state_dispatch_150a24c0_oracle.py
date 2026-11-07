"""Byte-backed record model, bounded service and original busy-service/caller windows."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ENTRY,SERVICE,BUSY,RECORD=0x150A24C0,0x15183290,0x800DDF5C,0x30000
WINDOW,END=0x150A1B44,0x150A1CF8
u32=lambda v:v&0xFFFFFFFF
signed16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    selector:int=1
    phase_byte:int=0
    mode:int=2
    pattern:int=0
    result:int=1
    mutation:int=0
    alias:int=0
    phase:int=0
    connected:int=0
def symbols():return dict(func_15183290=SERVICE)
def address(c):return(RECORD,STACK+c.phase-72,STACK+c.phase+4,0)[c.alias]
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[p+i]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[p+i]=b
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c=Case(),order='big'):
    m={STACK+c.phase+i:(i*17+165)&255 for i in range(-512,512)}
    if address(c):
        p=address(c)
        for i in range(52):m[p+i]=(i*29+90)&255
        for i,v in enumerate(((0x8000,0x7FFF,0xFFFF,0x8001),(0x7FFF,0x8000,0,0x7FFF),(0,0x1234,0x8001,0))[c.pattern]):wr(m,p+i*2,v,2,order)
        m[p+0x17]=c.mode&255
        wr(m,p+0x18,(0xFEDCBA98,0x800100FF,0x7FFF00A5)[c.pattern],4,order)
        wr(m,p+0x1C,(0xABCD0100,0x0011FF00,0xFFEEDD00)[c.pattern]|c.phase_byte,4,order)
        wr(m,p+0x20,(0x80000001,0xFFFFFFFF,0x12345678)[c.pattern],4,order)
    for i in range(4):m[BUSY+i]=(1,128,255,7)[i]
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-512<=p<STACK+c.phase+512}
def observed(m,c):return public(m,c),data(m,address(c),52)if address(c)else b''
def effect(m,c,order='big'):
    p=address(c)
    if c.mutation&1:m[p+0x17]=9
    if c.mutation&2:m[p+0x17]=2
    if c.mutation&4:wr(m,p+0x1C,0x76543210,4,order)
    if c.mutation&8:
        wr(m,p,0x13572468,4,order);wr(m,p+0x18,0x2468ACE0,4,order);wr(m,p+0x20,0xDEADBEEF,4,order)
def reference(initial,c=Case(),order='big',guest=True):
    m=dict(initial);p=address(c);home=STACK+c.phase;sp=home-64;calls=[]
    if guest:wr(m,home+4,c.selector,4,order)
    if u32(c.selector)!=255:
        state=rd(m,p+0x1C,4,order);low=state&255
        if low==0 or m[p+0x17]==9:
            # Snapshot the overlapping word/half/byte views before outgoing writes.
            mode=m[p+0x17];prop=rd(m,p+0x18,4,order);half=rd(m,p+0x18,2,order)
            b1a=m[p+0x1A];b1c=m[p+0x1C];b1d=m[p+0x1D];extra=rd(m,p+0x20,4,order)
            y=signed16(rd(m,p+2,2,order));x=signed16(rd(m,p,2,order));z=signed16(rd(m,p+4,2,order))
            if guest:wr(m,sp+16,mode,4,order)
            aux=signed16(rd(m,p+6,2,order))
            selector=rd(m,home+4,4,order)if guest else u32(c.selector)
            args=tuple(map(u32,(x,y+(b1d<<4),z,prop&255,mode,aux,selector,signed16(half),b1a,b1c,extra)))
            if guest:
                for off,value in((28,args[7]),(32,args[8]),(36,args[9]),(40,args[10]),(20,args[5]),(24,args[6])):wr(m,sp+off,value,4,order)
            calls.append((SERVICE,args))
            if c.connected:
                if guest:
                    for i,v in enumerate(args[:4]):wr(m,sp+4*i,v,4,order)
                result=0xFFFFFFFF
            else:
                effect(m,c,order);result=u32(c.result)
                if guest:
                    for i in range(4):wr(m,sp+4*i,0xB5000000+i,4,order)
            if result!=0xFFFFFFFF and m[p+0x17]!=9:
                wr(m,p+0x1C,(rd(m,p+0x1C,4,order)&0xFFFF0000)|u32(result<<8)|0xF0,4,order)
        else:wr(m,p+0x1C,(state&0xFFFFFF00)|max(2,low),4,order)
    return dict(memory=m,observed=observed(m,c),calls=calls)
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):
        super().__init__(words,memory,c,entry=entry,s=symbols(),connected=connected,arguments=(address(c),u32(c.selector)))
    def record_call(self,t):
        assert t in(ENTRY,SERVICE),hex(t)
        args=tuple(map(u32,self.arguments(2 if t==ENTRY else 11)))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        assert t==SERVICE
        effect(self.memory,self.case)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.result)
def helpers(rom,c):
    return dict(zip(range(SERVICE,SERVICE+1568,4),struct.unpack_from('>392I',rom,0x1B0740)))if c.connected else{}
def state(m,full=True):
    registers=m.r if full else[m.r[i]for i in(*range(16,24),28,29,30,31)]
    return(m.memory,registers,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def caller_machine(rom,body,c,offset):
    initial=fixture(c);home=STACK+c.phase;wr(initial,home+0xC8,c.selector)
    code=helpers(rom,c);code.update(zip(range(ENTRY,ENTRY+276,4),body));code[END]=0
    machine=Oracle(list(struct.unpack_from('>5I',rom,0xCEFF4)),initial,c,entry=WINDOW,connected=code)
    machine.r[16]=u32(address(c)-offset);machine.r[3]=u32(offset)
    machine.code=WindowCode(machine.code,machine);machine.code.ends=(END,)
    expected=reference(initial,c);expected['calls'].insert(0,(ENTRY,(address(c),u32(c.selector))))
    return machine,expected
def cases():
    for phase,mode,pattern in itertools.product(range(256),(0,2,9,255),range(3)):yield Case(phase_byte=phase,mode=mode,pattern=pattern)
    for mode in range(256):yield Case(mode=mode,phase_byte=1)
    for selector,result,mutation,pattern in itertools.product((255,-1,256,0x100FF,0x80000000,0x7FFFFFFF),(0,1,2,3,-1,0x12345678,0x80000000),(0,1,2,4,8,7,14),range(3)):
        yield Case(selector=selector,result=result,mutation=mutation,pattern=pattern,mode=9 if mutation==2 else 2)
    for alias,phase,low,mode,mutation in itertools.product((1,2),(0,8),(0,1,2,255),(2,9),(0,1,4,14)):
        yield Case(alias=alias,phase=phase,phase_byte=low,mode=mode,mutation=mutation)
    yield Case(alias=3,selector=255)
