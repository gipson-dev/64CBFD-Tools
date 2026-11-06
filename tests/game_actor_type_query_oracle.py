"""Ordered actor queries and bit-preserving O32 arguments; bounded providers."""
from dataclasses import dataclass
import struct
from tools.experiments import game_actor_type_query_candidates as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ACTORS,END,META,LOOKUP,QUERY=0x800cc2d0,0x800d121c,0x8009bd30,0x1508108c,0x15080d20
ORIGIN,OUTPUT,ALT_OUTPUT,LOG=0x60000,0x70000,0x71000,0x72000
FLOATS=(0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,1,0x7f7fffff)
@dataclass(frozen=True)
class Case:
    actor_type:int=83
    mode:int=15
    match_at:int=0
    part:int=3
    result:int=1
    busy:int=1
    loaded:bool=True
    kind:int=83
    forward:int=0x42200000
    radius:int=0x41200000
    phase:int=0
    mutation:int=0
    alias:int=0
    origin:int=ORIGIN
    output:int=OUTPUT

def sym(s=None):return dict(dict(ACTORS=ACTORS,END=END,META=META,LOOKUP=LOOKUP,QUERY=QUERY),**(s or {}))
def homes(c):return STACK+c.phase,STACK+c.phase-80
def output(c):
    h,sp=homes(c);return (c.output,h+16,h+20,c.output)[c.alias]
def fixture(c=Case(),s=None):
    s=sym(s);h,sp=homes(c);m={STACK+i:(i*17+165)&255 for i in range(-1024,512)}
    for p,n in((s['ACTORS'],25*0x32c),(c.origin,0x32c),(c.output,16),(ALT_OUTPUT,16),(LOG,16)):
        m.update({p+i:(i*13+90)&255 for i in range(n)})
    for i in range(25):
        a=s['ACTORS']+i*0x32c;put(m,a,c.busy if i>=c.match_at else 0);put(m,a+0x1d4,0x12345678 if c.loaded else 0);put(m,a+4,c.kind,1)
    for i in range(-8,256):
        p=s['META']+4*i;m.update({p+j:(i*11+j+7)&255 for j in range(4)});put(m,p,(i+5)&255,2)
    put(m,h+16,c.mode&0xffffffff);put(m,h+20,c.actor_type&0xffffffff);put(m,LOG,0)
    return m
def lookup_result(c,a,s):
    i=(a-s['ACTORS'])//0x32c
    return 0xffffffff if c.part==-1 else (c.part+(i%3 if c.mutation&16 else 0))&0xffffffff
def query_result(c,a,s):
    i=(a-s['ACTORS'])//0x32c
    return 0 if c.mutation&32 and i<24 else c.result&0xffffffff
def effect(m,c,target,args,s):
    h,sp=homes(c)
    if target==LOOKUP:
        if c.mutation&1:
            put(m,args[0],0);put(m,args[0]+0x1d4,0);put(m,args[0]+4,c.kind^255,1)
        if c.mutation&2:put(m,h+12,ALT_OUTPUT);put(m,h+16,0x80000000);put(m,h+20,0xffffffff)
        if c.mutation&4:
            i=lookup_result(c,args[0],s)
            if i!=0xffffffff:put(m,(s['META']+4*i+2)&0xffffffff,255,1)
    else:
        if c.mutation&8:put(m,h+12,ALT_OUTPUT);put(m,output(c),0xdeadbeef)
        put(m,LOG,read(m,LOG)+1)
def scratch(m,sp):
    for i in range(4):put(m,sp+4*i,0xb5000000+i)
def part_reference(m,a,s):
    kind=read(m,a+4,1)
    for i in range(23):
        if read(m,s['META']+4*i,2)==kind:return i
    return 0xffffffff
def reference(initial,c,before,f,s=None,connected=False,ra=None):
    s=sym(s);m=dict(initial);h,sp=homes(c);calls=[]
    put(m,sp+0x28,(f[23]<<32)|f[22],8);put(m,sp+0x20,(f[21]<<32)|f[20],8)
    for reg in (*range(16,23),31):put(m,sp+(0x4c if reg==31 else 0x30+4*(reg-16)),before[reg] if reg!=31 or ra is None else ra)
    put(m,h+12,output(c));put(m,read(m,h+12),0);query_mode,actor_type=read(m,h+16),read(m,h+20);value=0
    for i in range(25):
        actor=s['ACTORS']+0x32c*i
        if read(m,actor) and read(m,actor+0x1d4) and read(m,actor+4,1)==actor_type:
            calls.append((LOOKUP,(actor,)))
            if connected:part=part_reference(m,actor,s)
            else:effect(m,c,LOOKUP,(actor,),s);part=lookup_result(c,actor,s);scratch(m,sp)
            if part!=0xffffffff:
                args=(c.origin,actor,read(m,(s['META']+4*part+2)&0xffffffff,1),c.forward,c.radius,query_mode)
                put(m,sp+20,query_mode);put(m,sp+16,c.radius);calls.append((QUERY,args));effect(m,c,QUERY,args,s);scratch(m,sp);value=query_result(c,actor,s)
                if value:put(m,read(m,h+12),actor);break
    return m,calls,value
class Oracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,s=None,arguments=None):
        self.c,self.s=c,sym(s);self.trace=[]
        args=(c.origin,c.forward,c.radius,output(c),c.mode&0xffffffff,c.actor_type&0xffffffff)
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=args if arguments is None else arguments,connected=connected)
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction:self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        counts={source.ENTRY:6,self.s['LOOKUP']:1,self.s['QUERY']:6}
        if t not in counts:raise AssertionError(('Unbounded query provider',hex(t)))
        args=tuple(self.arguments(counts[t]));canonical=LOOKUP if t==self.s['LOOKUP']else QUERY if t==self.s['QUERY']else t;self.calls.append((canonical,args));self.events.append(('CALL',canonical,args))
    def hook(self,t):
        canonical,args=self.calls[-1];effect(self.memory,self.c,canonical,args,self.s)
        value=lookup_result(self.c,args[0],self.s) if canonical==LOOKUP else query_result(self.c,args[1],self.s)
        scratch(self.memory,self.r[29])
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def lookup_code(rom):return dict(zip(range(LOOKUP,0x1508114c,4),struct.unpack_from('>48I',rom,0xae53c)))
def external(events):return[e for e in events if e[0]not in('R','W')or not STACK-1024<=e[1]<STACK+512]
def state(m):return m.memory,m.r,m.f,m.events,m.calls,m.current_pc,m.delay_of,m.root_accesses,m.hi,m.lo,m.trace
