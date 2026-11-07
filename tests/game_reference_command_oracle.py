"""Independent byte-memory reference for cleanup and owner exchange commands."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
ENTRY,FREE,REPAIR,DEFAULT=0x151347CC,0x1516972C,0x151696DC,0x15169804
RECORD,REQUEST,MARK,TABLE,CALLBACK=0x30040,0x50000,0x70000,0x8008B4D0,0x17400200
@dataclass(frozen=True)
class Case:
    command:int=0
    situation:int=0
    alias:int=0
    state:int=5
    phase:int=0
    high:int=0
    kind:int=40
    cleanup:int=0
    mutation:int=0
def request(c):return (REQUEST,RECORD-8,RECORD,RECORD+0x10,RECORD+0x14,RECORD+0x18,RECORD+0x1C,RECORD+0x20,0)[c.alias]
def args(c):return (RECORD,request(c),(c.high&0xFFFFFF00)|(c.command&255))
def fixture(c):
    m={STACK+c.phase+i:(i*17+165)&255 for i in range(-512,512)}
    for base,n in((RECORD-64,256),(REQUEST,32),(MARK,8)):
        m.update({base+i:(i*29+90)&255 for i in range(n)})
    q=request(c);first,second,current=((0x11112222,0x33334444,0x11112222),(0x11112222,0x33334444,0x33334444),(0x11112222,0x33334444,0x55556666),(q,0x12345678,q),(0,0,0),(0xFFFFFFFF,0x80000000,0xFFFFFFFF),(RECORD,REQUEST,RECORD),(REQUEST,RECORD,RECORD))[c.situation]
    if q:
        put(m,q,first);put(m,q+4,second);m[q+8]=0x51;m[q+9]=0xA2
    put(m,RECORD+0x1C,current);m[RECORD+0x18]=0x33 if c.situation%2 else(m[q+4]if q else 0x33)
    m[RECORD+0x3D]=c.state;m[RECORD]=c.kind
    for kind in(2,31,40):put(m,TABLE+kind*52,CALLBACK if c.cleanup==2 else 0)
    return m
def public(m,c):return {a:b for a,b in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+512}
def effect(m,c,which):
    put(m,MARK,0x12345678 if which==FREE else 0xABCDEF01)
    if c.mutation:m[RECORD]=2;m[RECORD+0x18]^=0x5A;put(m,RECORD+0x1C,0x87654321)
def reference(initial,c):
    m=dict(initial);q=request(c);cmd=c.command&255;calls=[]
    cleanup=False
    if cmd in(0,3,17):
        if cmd!=17 or m[RECORD+0x3D]==5:
            cleanup=read(m,RECORD+0x1C)==read(m,q)or m[RECORD+0x18]==m[q+4]
    elif cmd==22:cleanup=q==read(m,RECORD+0x1C)
    elif cmd==45:
        pair=(read(m,q),read(m,q+4));current=read(m,RECORD+0x1C)
        side=0 if pair[0]==current else 1 if pair[1]==current else None
        if side is not None:
            put(m,RECORD+0x1C,pair[1-side]);m[RECORD+0x18]=m[q+9-side]
    if cleanup:
        calls.append((FREE,(RECORD,)))
        if not c.cleanup:effect(m,c,FREE)
        else:
            calls.append((REPAIR,(RECORD,)));effect(m,c,REPAIR)
            if m[RECORD]>=2:
                target=read(m,TABLE+m[RECORD]*52)
                calls.append((target or DEFAULT,(RECORD,)));effect(m,c,target or DEFAULT)
    return public(m,c),calls
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=args(c)if arguments is None else arguments)
        self.c=c
    def record_call(self,t):
        assert t in(ENTRY,FREE,REPAIR,DEFAULT,CALLBACK),hex(t)
        a=tuple(self.arguments(3 if t==ENTRY else 1));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t in(FREE,REPAIR,DEFAULT,CALLBACK),hex(t);effect(self.memory,self.c,t)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def helpers(rom,c):
    return dict(zip(range(FREE,FREE+112,4),struct.unpack_from('>28I',rom,0x196BDC)))if c.cleanup else {}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.events,m.calls,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for command,situation,alias,state,phase,high in itertools.product(range(256),range(4),(0,4),(0,5),(0,8),(0,0xABCDEF00)):
        yield Case(command,situation,alias,state,phase,high)
    for command,situation,alias,state in itertools.product((0,3,17,22,45),range(8),range(8),(0,5,255)):
        yield Case(command,situation,alias,state)
