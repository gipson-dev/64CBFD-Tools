"""Bounded record dispatcher; helper hooks and connected-helper claims are separate."""
from dataclasses import dataclass
import struct
from tools.experiments import game_group_record_actor_dispatch_candidates as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
MASK1,MASK2,RECORDS,COUNT=0x800c35d0,0x800c35c8,0x800c35f0,0x800c363a
LOOKUP,UPDATE=0x15083e90,0x1502178c
A,B,R,ALT_A,ALT_B,ALT_R,ACTOR,OUTPUT=0x20000,0x21000,0x24000,0x28000,0x29000,0x2c000,0x60000,0x50000

@dataclass(frozen=True)
class Case:
    count:int=3
    group:int=0
    mask1:int=1
    mask2:int=1
    kind:int=2
    actor_id:int=7
    mode:int=0
    pattern:int=0
    phase:int=0
    alias:int=0

def slots(c,s=None):
    s=s or {};return tuple((s.get(n,a)+c.group*stride)&0xffffffff for n,a,stride in (('D_800C35D0',MASK1,4),('D_800C35C8',MASK2,4),('D_800C35F0',RECORDS,4),('D_800C363A',COUNT,1)))

def fixture(c=Case(),s=None):
    m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
    for p,n in ((A,512),(B,512),(R,2048),(ALT_A,512),(ALT_B,512),(ALT_R,2048),(ACTOR,1024),(OUTPUT,32)):
        m.update({p+i:(i*13+0x5a)&255 for i in range(n)})
    a,b,r,n=slots(c,s);put(m,a,A);put(m,b,A if c.alias else B);put(m,r,R);put(m,n,c.count,1);put(m,OUTPUT,0)
    for i in range(256):
        g1,g2,k=c.mask1,c.mask2,c.kind
        if c.pattern: g1,g2,k=((0,1,0xffff,0x8000,1)[i%5],(1,0,0x100,1,1)[i%5],(2,2,2,0x102,2)[i%5])
        for at,value,size in ((A+2*i,g1,2),(B+2*i,g2,2),(R+8*i,k,2),(R+8*i+2,(c.actor_id+i)&255,1),(ALT_A+2*i,1,2),(ALT_B+2*i,1,2),(ALT_R+8*i,2,2),(ALT_R+8*i+2,(255-i)&255,1)): put(m,at,value,size)
    return m

def result(actor_id): return 0 if actor_id%3==1 else ACTOR+4*(actor_id%4)

def effect(m,c,target,args,ordinal,s=None):
    a,b,r,n=slots(c,s)
    if target==LOOKUP:
        if c.mode==1: put(m,n,0,1)
        elif c.mode==2: put(m,n,min(255,c.count+2),1)
        elif c.mode==3: put(m,a,ALT_A);put(m,b,ALT_B);put(m,r,ALT_R);put(m,n,4,1)
        elif c.mode==4:
            put(m,read(m,r)+2,255,1);put(m,read(m,r),0xffff,2)
    else:
        if c.mode==5: put(m,n,0,1)
        elif c.mode==6:
            put(m,n,4,1);put(m,read(m,a)+2,0,2)
        put(m,OUTPUT,read(m,OUTPUT)+1);put(m,args[0],(args[1]^args[2]^0x87654321)&0xffffffff)

def scratch(m,sp):
    for i in range(4): put(m,sp+4*i,0xb5000000+i)

def reference(initial,c,before,s=None,connected=False):
    m=dict(initial);sp=STACK+c.phase-64;calls=[]
    for reg in (*range(16,24),30,31): put(m,sp+(0x38 if reg==30 else 0x3c if reg==31 else 0x18+4*(reg-16)),before[reg])
    a,b,r,n=slots(c,s);count=read(m,n,1);index=0
    while index<count:
        if read(m,read(m,a)+index*2,2) and read(m,read(m,b)+index*2,2):
            rec=read(m,r)+8*index
            if read(m,rec,2)==2:
                actor_id=read(m,rec+2,1);calls.append((LOOKUP,(actor_id,)))
                if connected:
                    found=0
                    if actor_id:
                        for i in range(26):
                            p=0x800cc2d0+i*0x32c
                            if read(m,p) and read(m,p+0x3b,1)==actor_id: found=p;break
                    # The original lookup stores its incoming u8 argument home.
                    put(m,sp,actor_id)
                else:
                    effect(m,c,LOOKUP,(actor_id,),len(calls),s);scratch(m,sp);found=result(actor_id)
                if found:
                    args=(found,c.group&0xffffffff,index);calls.append((UPDATE,args));effect(m,c,UPDATE,args,len(calls),s);scratch(m,sp)
            count=read(m,n,1)
        index+=1
    return m,calls

class Oracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,s=None,arguments=None):
        self.c,self.s=c,s or {};self.trace=[]
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.group&0xffffffff,) if arguments is None else arguments,connected=connected)
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction: self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.recording and self.own_instruction: self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        lookup=self.s.get('func_15083E90',LOOKUP);update=self.s.get('func_1502178C',UPDATE)
        count=1 if t in (source.ENTRY,lookup) else 3 if t==update else None
        if count is None: raise AssertionError(('Unbounded group provider',hex(t)))
        args=tuple(self.arguments(count));canonical=LOOKUP if t==lookup else UPDATE if t==update else t
        self.calls.append((canonical,args));self.events.append(('CALL',canonical,args))
    def hook(self,t):
        canonical,args=self.calls[-1];effect(self.memory,self.c,canonical,args,len(self.calls),self.s)
        value=result(args[0]) if canonical==LOOKUP else 0xdeadbeef
        scratch(self.memory,self.r[29])
        for r in (1,2,3,*range(4,16),24,25): self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def connected_fixture(c):
    m=fixture(c)
    for i in range(26):
        p=0x800cc2d0+i*0x32c;m.update({p+j:0 for j in range(0x40)});put(m,p,0 if i%5==1 else 0x12345678);put(m,p+0x3b,(i*11+c.actor_id)&255,1)
    return m

def lookup_code(rom):
    return dict(zip(range(LOOKUP,0x15083fb0,4),struct.unpack_from('>72I',rom,0xb1340)))

def external(events):
    return [e for e in events if e[0] not in ('R','W') or not STACK-1024<=e[1]<STACK+512]

def state(m):
    return m.memory,m.r,m.f,m.events,m.calls,m.current_pc,m.delay_of,m.root_accesses,m.hi,m.lo,m.trace
