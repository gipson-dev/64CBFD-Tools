"""Mutable command buffers, the original ring reader and channel dispatcher."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_channel_command_poller_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import game_actor_channel_command_oracle as channel
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ENTRY,READER,ACTION=source.ENTRY,0x100126E8,0x15080430
RECEIVE,TRANSFER,SKIP,COPY=0x15043CA4,0x15043AC8,0x15043B70,0x10022EC0
QUEUE,RING,MARK=0x800427A0,0x30000,0x50000
INDEX,BASE,MODE=0x800D18D0,0x800CC2D0,0x800D1928
COUNT,APPLY=0x1507E968,0x1507E500
u32=lambda n:n&0xFFFFFFFF
def packet(opcode=0x4C,command=3,value=734,high=0,length=8):
    data=bytearray([opcode,17,29,command,*[((value>>shift)&127)|high for shift in(21,14,7,0)]])
    data.extend((i*29+89)&255 for i in range(max(0,length-8)))
    return bytes(data[:length])
@dataclass(frozen=True)
class Case:
    messages:tuple=(packet(),packet(0x41),packet(value=0))
    statuses:tuple=()
    index:int=3
    mode:int=0
    active:int=1
    phase:int=0
    seed:int=0
    connected:int=0
    alias:bool=False
    cursor:int=2041

def symbols():return dict(func_100126E8=READER,func_15080430=ACTION,D_800D18D0=INDEX,D_800CC2D0=BASE)
def buffer(home):return home-256
def ring(c,home):return buffer(home)if c.alias else RING
def ring_size(c):return 64 if c.alias else 2048
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
    for n,k in itertools.product(range(len(c.messages)+2),repeat=2):
        index=(c.index+(37*n if c.mode&1 else 0)+17*k)&255;p=s['D_800CC2D0']+index*0x32C
        m.update({p+i:(i*13+c.seed)&255 for i in range(0x210)})
    m[s['D_800D18D0']]=c.index;put(m,MODE,0x12345678);put(m,MARK,0)
    base,size=ring(c,home),ring_size(c);m.update({base+i:(i*29+89)&255 for i in range(size)});start=c.cursor%size;cursor=start
    for data in c.messages:
        for byte in struct.pack('>I',len(data))+data:m[base+cursor]=byte;cursor=(cursor+1)%size
    for offset,value in((0,base),(4,size),(8,start),(12,cursor)):put(m,QUEUE+offset,value)
    return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+1024}
def request_effect(m,c,s,n):
    put(m,MARK,n)
    if c.mode&1:m[s['D_800D18D0']]=(c.index+n*37)&255
def action_effect(m,c,s,home):
    if c.mode&2:m[s['D_800D18D0']]=(m[s['D_800D18D0']]+17)&255
    if c.mode&4:
        p=buffer(home);m[p+3]^=255
        for i,b in enumerate((0xFF,0x80,0x81,0x82)):m[p+4+i]=b
def receive(m,dest):
    size=read(m,QUEUE+4);cursor=read(m,QUEUE+8)
    if cursor==read(m,QUEUE+12):return 0
    base=read(m,QUEUE)
    def pull(n):
        nonlocal cursor
        value=bytes(m[base+(cursor+i)%size]for i in range(n));cursor=(cursor+n)%size;return value
    length=int.from_bytes(pull(4),'big');assert length<4096
    count=min(length,255 if length>256 else 256);value=pull(count)
    for i,b in enumerate(value):m[dest+i]=b
    if length>256:m[dest+255]=0;cursor=(cursor+length-count)%size
    put(m,QUEUE+8,cursor);return length
def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;m=dict(initial);p=buffer(home);calls=[];actions=[];n=0
    while True:
        calls.append((s['func_100126E8'],(p,256)));request_effect(m,c,s,n+1)
        if c.connected&1:status=receive(m,p)
        elif n<len(c.messages):
            for i,b in enumerate(c.messages[n]):m[p+i]=b
            status=c.statuses[n]if c.statuses else len(c.messages[n])
        else:status=0
        n+=1
        if not status:break
        if m[p]!=0x4C:continue
        value=sum((m[p+4+i]&127)<<(21-7*i)for i in range(4))//367
        a=(s['D_800CC2D0']+m[s['D_800D18D0']]*0x32C,u32(m[p+3]-1),value or 20);calls.append((s['func_15080430'],a));actions.append(a);action_effect(m,c,s,home)
        if c.connected&2:
            m,child=channel.reference(m,channel.Case(channel=a[1],duration=a[2],count=c.active,owner=a[0]));calls+=child
        if n>64:raise AssertionError('Unbounded packet fixture')
    return dict(memory=m,calls=calls,actions=actions,reads=n)

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=()):
        self.s=symbols()if s is None else s;self.n=0;self.submissions=[];self.home=STACK+c.phase
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=arguments)
    def record_call(self,t):
        counts={self.s['func_100126E8']:2,self.s['func_15080430']:3,RECEIVE:3,TRANSFER:5,SKIP:4,COPY:3,COUNT:1,APPLY:3,ENTRY:0,0x1501E1B4:1,0x151F2CDC:0}
        assert t in counts,hex(t);a=tuple(u32(v)for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t==self.s['func_100126E8']:self.n+=1;request_effect(self.memory,self.case,self.s,self.n)
        if t==self.s['func_15080430']:self.submissions.append(a);action_effect(self.memory,self.case,self.s,self.home)
    def hook(self,t):
        c=self.case;a=self.calls[-1][1]
        if t==self.s['func_100126E8']:
            assert a==(buffer(self.home),256)
            if self.n<=len(c.messages):
                data=c.messages[self.n-1]
                for i,b in enumerate(data):self.memory[a[0]+i]=b
                value=c.statuses[self.n-1]if c.statuses else len(data)
            else:value=0
        elif t==self.s['func_15080430']:value=0x87654321
        elif t==COUNT:value=c.active
        elif t==APPLY:value=0x87654321
        elif t==COPY:
            assert a[2]<=2048;data=bytes(self.memory[a[1]+i]for i in range(a[2]))
            for i,b in enumerate(data):self.memory[a[0]+i]=b
            value=a[0]
        elif t==0x1501E1B4:value=0x87654321
        elif t==0x151F2CDC:value=self.gate
        else:raise AssertionError(('Unbounded packet service',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(value);self.hi,self.lo=0xA5000010,0xA5000011
def helper_code(rom,c):
    result={}
    entries=[(READER,12),(RECEIVE,58),(TRANSFER,42),(SKIP,18),(COPY,11)]if c.connected&1 else[]
    if c.connected&2:entries.append((ACTION,51))
    for entry,n in entries:
        offset=entry-0x10000000 if entry<0x15000000 else entry-0x15000000+0x2D4B0
        result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return result
def cases():
    for i in range(256):yield Case(messages=(packet(command=i,value=(i*1048573)&0xFFFFFFF,high=128),),index=i,mode=i%8,phase=(i%2)*8)
    for value,mode,phase in itertools.product((0,1,366,367,368,733,734,0xFFFFFFF),(0,7),(0,8)):yield Case(messages=(packet(value=value),packet(0x41),packet(value=value^127)),mode=mode,phase=phase)
    for opcode in range(256):yield Case(messages=(packet(opcode=opcode),))
    for status in(1,0x7FFFFFFF,0x80000000,0xFFFFFFFF):yield Case(statuses=(status,status,status),mode=7)
    yield Case(messages=());yield Case(messages=(b'',packet()))
    yield Case(messages=(packet(),packet(length=4)),mode=4)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.submissions)
