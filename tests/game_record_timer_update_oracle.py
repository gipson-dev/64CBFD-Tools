"""Timer record guest semantics and original frame-update call boundary."""
from dataclasses import dataclass
import struct
from tools.experiments import game_record_timer_update_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    flags:int=0xCC
    ticks:int=1
    value:int=0
    elapsed:int=1
    pattern:int=0
    mixed:bool=False
    alias:int=0
    phase:int=0

def symbols(base=0x800D3010,table=0x80088510,delta=0x800BE9E4):return dict(D_800D3010=base,D_800D3088=u32(base+120),D_80088510=table,D_8008851C=u32(table+12),D_800BE9E4=delta)
def fixture(c=Case(),s=None):
    s=symbols()if s is None else dict(s)
    if c.alias==1:s['D_800BE9E4']=s['D_800D3010']+4
    if c.alias==2:s['D_800BE9E4']=s['D_800D3010']+8
    if c.alias==3:s['D_80088510']=s['D_800D3010'];s['D_8008851C']=s['D_800D3010']+12
    m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for base,size in((s['D_800D3010'],124),(s['D_80088510'],44),(s['D_800BE9E4'],4)):
        for i in range(size):m[u32(base+i)]=165
    for i in range(22):
        v=((2,6,60,3600,20864,0,0,10,60,60,24,0,0,0,0,0,0x2564,0x0A00,0,0,0,0)[i]if c.pattern==0 else(0,1,3,65535,32768,7)[(i+c.pattern)%6])
        put(m,u32(s['D_80088510']+2*i),v,2)
    put(m,s['D_800BE9E4'],u32(c.ticks))
    for i in range(10):
        base=u32(s['D_800D3010']+12*i);flag=(c.flags+(i*17 if c.mixed else 0))&255
        put(m,base,(flag<<24)|(0x12345+i));put(m,u32(base+4),u32(c.value+(i if c.mixed else 0)));put(m,u32(base+8),u32(c.elapsed+(i if c.mixed else 0)))
    return m,s

def reference(initial,s):
    m=dict(initial)
    for i in range(10):
        b=u32(s['D_800D3010']+12*i);header=read(m,b)
        if header&0xC0000000!=0xC0000000:continue
        k=(header>>26)&15;old=read(m,u32(b+8));delta=read(m,s['D_800BE9E4']);period=read(m,u32(s['D_80088510']+k*2),2);elapsed=u32(old+delta);put(m,u32(b+8),elapsed)
        if elapsed<period:continue
        value=u32(read(m,u32(b+4))+1);limit=read(m,u32(s['D_8008851C']+k*2),2)
        put(m,u32(b+8),u32(elapsed-period));put(m,u32(b+4),value)
        if limit:put(m,u32(b+4),value%limit)
    return m

class TimerOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None):
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(),connected=connected)
        self.trace=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,a,n):
        v=super().get(a,n)
        if self.own_instruction:self.trace.append(('R',a,n,v))
        return v
    def put(self,a,v,n):
        super().put(a,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        assert t==source.ENTRY,hex(t);self.calls.append((t,()));self.events.append(('CALL',t,()))
    def hook(self,t):raise AssertionError(('Unbounded timer provider',hex(t)))

CALLER=0x1501A204
def caller_machine(rom,words,c=Case()):
    initial,s=fixture(c);body=struct.unpack_from('>6I',rom,CALLER-0x15000000+0x2D4B0);connected=dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
    m=TimerOracle(body,initial,c,entry=CALLER,connected=connected)
    # The window enters after the parent's 24-byte frame has been allocated.
    # Its epilogue restores the caller's pre-frame stack, not the window entry SP.
    m.before[29]=u32(STACK+c.phase+24)
    put(m.memory,STACK+c.phase+20,m.r[31]);initial=dict(m.memory);return m,reference(initial,s)
