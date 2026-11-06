"""Signed row selection and ordered float comparisons; no FCSR/hardware claim."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_event_height_threshold_candidates as source
from tools.tests.game_table_payload_spawn_oracle import Oracle as InstructionOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
LOOKUP,POINT,DISPATCH=0x151CE634,0x1515C1A0,0x1505D024
RAW_ENTRY=0x15200000  # The unpadded 72-word body must not overlap LOOKUP.
ACTOR,EVENT,OWNER,TABLE,OTHER_TABLE,PAYLOAD=0x30000,0x32000,0x40000,0x50000,0x80000,0x60000
HEADS,END,COLUMNS=0x800DCE50,0x800DD190,0x800A5760
SYMS=dict(func_151CE634=LOOKUP,func_1515C1A0=POINT,func_1505D024=DISPATCH)
FLOAT_CASES=((0x40800000,0x3f800000,0x40400000),(0x40800000,0x3f800000,0x40a00000),(0,0x80000000,0),(0x80000000,0,0x80000000),(0x7f800000,0x3f800000,0x7f800000),(0xff800000,0xbf800000,0xff800000),(0x7f800000,0x7f800000,0),(0x3f800000,0x7fc12345,0),(0x7f812345,0,0),(0,0,0x7fc12345),(1,0x80000001,1),(0x7f7fffff,0xff7fffff,0x7f800000))
@dataclass(frozen=True)
class Case:
    found:bool=True
    flags:int=8
    count:int=1
    previous:int=1
    fallback:int=1
    current:int=0
    y:int=0x40800000
    height:int=0x3f800000
    limit:int=0x40400000
    mutation:int=0
    phase:int=0
    seed:int=0
    actor_id:int=0
    radius_half:int=2
    height_half:int=3
    offset_half:int=-1
    column:int=0
    lookup_phase:int=0
    context:int=0x12345678
    actor:int=ACTOR
def s8(v):return((v&255)^128)-128
def s16(v):return((v&65535)^32768)-32768
def home(c):return STACK+c.phase
def scratch(m,sp):
    for i in range(4):put(m,sp+4*i,0xb5000000+i)
def query_effect(m,c):
    if c.mutation&2:
        put(m,OWNER+0x1e,read(m,OWNER+0x1e,2)^8,2);m[OWNER+0x2d]^=128;m[OWNER+0x2e]=0;m[OWNER+0x25]=0;put(m,OWNER+0x94,OTHER_TABLE)
    if c.mutation&4:put(m,home(c),c.actor+0x400)
    if c.mutation&16:m[OWNER+0x2c]=128
def selection(m):
    if s8(m[OWNER+0x2c])<=0:return None
    if read(m,OWNER+0x1e,2)&8:
        index=s8(m[OWNER+0x2e])-1
        if index<0:index=m[OWNER+0x25]-1
    else:index=s8(m[OWNER+0x2d])
    return(read(m,OWNER+0x94)+28*index+4)&0xffffffff
def fixture(c=Case()):
    m={STACK+i:(i*17+c.seed*7+165)&255 for i in range(-512,512)}
    for base,n in((c.actor,0x32c),(c.actor+0x400,0x32c),(EVENT,32),(OWNER,0xa0),(PAYLOAD,0x50),(HEADS,0x340),(COLUMNS,8)):
        m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
    for actor in(c.actor,c.actor+0x400):
        m[actor+4]=c.actor_id&255
        for at,v,n in((0x14,0x3f800000,4),(0x18,c.y,4),(0x1c,0xc0400000,4),(0xd2,c.radius_half,2),(0xd4,c.height_half,2),(0xd6,c.offset_half,2)):put(m,actor+at,v&((1<<(8*n))-1),n)
    put(m,EVENT+0x18,c.context);put(m,OWNER+0x1e,c.flags,2);put(m,OWNER+0x20,11);put(m,OWNER+8,0);put(m,OWNER+0x98,PAYLOAD);put(m,PAYLOAD+0x48,c.context);put(m,OWNER+0x94,TABLE)
    for off,v in((0x25,c.fallback),(0x2c,c.count),(0x2d,c.current),(0x2e,c.previous)):m[OWNER+off]=v&255
    for table in(TABLE,OTHER_TABLE)if c.mutation&2 else(TABLE,):
        for index in range(-128,256):
            base=table+28*index;m.update({base+i:(i*13+index*7+c.seed)&255 for i in range(28)});put(m,base+4,bits(float(index%23-11)))
    projected=dict(m);query_effect(projected,c);target=selection(projected)
    if target is not None:put(m,target,c.limit)
    # Build both phase columns with wrong-kind and wrong-context nodes. Only
    # the selected phase's second row may reach the actual height owner.
    for i in range(0x340//4):put(m,HEADS+4*i,0)
    for phase,column in enumerate((c.column%104,(c.column+1)%104)):
        put(m,COLUMNS+4*phase,column)
        for row in range(2):
            node=0x42000+(2*phase+row)*0x1000;payload=node+0x200
            m.update({node+i:0xa5 for i in range(0xa0)});m.update({payload+i:0x5a for i in range(0x50)})
            put(m,HEADS+row*0x1a0+4*column,node);put(m,node+0x20,10 if row==0 else 11);put(m,node+0x98,payload);put(m,payload+0x48,c.context^1);put(m,node+8,OWNER if c.found and phase==c.lookup_phase and row==1 else 0)
    return m
def point_values(c,connected=False):
    y=c.y;radius=0x3f800000;extent=c.height
    if connected:
        if(c.actor_id&255)<0xbb and(c.actor_id&255)!=255:
            radius=bits(float(s16(c.radius_half)));extent=bits(float(s16(c.height_half)));y=bits(floating(y)+float(s16(c.offset_half)))
        else:radius=extent=0x3f800000
    return(0x3f800000,y,0xc0400000),radius,extent
def reference(initial,c=Case(),ra=0xa000001f,connected=False,s=SYMS):
    m=dict(initial);h=home(c);sp=h-80;calls=[];reads=[];put(m,sp+20,ra);put(m,h,c.actor);calls.append((s['func_151CE634'],(c.context,)))
    if not connected:
        if c.mutation&1:put(m,h,c.actor+0x400)
        scratch(m,sp)
    if not c.found:return m,calls,reads
    actor=read(m,h);put(m,sp+56,OWNER);calls.append((s['func_1515C1A0'],(actor,sp+68,sp+64,sp+60)))
    if not connected:query_effect(m,c)
    points,radius,extent=point_values(c,connected)
    put(m,sp+64,radius);put(m,sp+60,extent)
    for i,v in enumerate(points):put(m,sp+68+4*i,v)
    if not connected:scratch(m,sp)
    target=selection(m)
    if target is not None:
        reads.append((target,4));boundary=bits(floating(points[1])-floating(extent))if read(m,OWNER+0x1e,2)&8 else bits(floating(points[1])+floating(extent));limit=read(m,target)
        triggered=floating(boundary)<=floating(limit)if read(m,OWNER+0x1e,2)&8 else floating(limit)<=floating(boundary)
        if triggered:
            a=(read(m,h),0x60019,0,0xffffffff);calls.append((s['func_1505D024'],a));put(m,a[0]+0x20,0x13579bdf);scratch(m,sp)
    return m,calls,reads
class Oracle(InstructionOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,s=SYMS,arguments=None):
        self.c,self.s=c,s;TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.actor,EVENT)if arguments is None else arguments,connected=connected);self.trace=[]
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction:self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        counts={source.ENTRY:2,self.s['func_151CE634']:1,self.s['func_1515C1A0']:4,self.s['func_1505D024']:4}
        if t not in counts:raise AssertionError(('Unbounded height provider',hex(t)))
        a=tuple(v&0xffffffff for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        c=self.c;a=self.calls[-1][1];value=0xdeadbeef
        if t==self.s['func_151CE634']:
            if c.mutation&1:put(self.memory,home(c),c.actor+0x400)
            value=OWNER if c.found else 0
        elif t==self.s['func_1515C1A0']:
            query_effect(self.memory,c);points,radius,extent=point_values(c)
            for i,v in enumerate(points):put(self.memory,a[1]+4*i,v)
            put(self.memory,a[2],radius);put(self.memory,a[3],extent)
        elif t==self.s['func_1505D024']:put(self.memory,a[0]+0x20,0x13579bdf)
        else:raise AssertionError(('Unowned height helper',hex(t)))
        scratch(self.memory,self.r[29])
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def helper_code(rom):
    code={}
    for entry,end in((LOOKUP,0x151ce6d0),(POINT,0x1515c244)):
        at=entry-0x15000000+0x2d4b0;n=(end-entry)//4;code.update(zip(range(entry,end,4),struct.unpack_from('>%dI'%n,rom,at)))
    return code
def table_reads(model):return[(p,n)for op,p,n,v in model.trace if op=='R'and any(base-128*28<=p<base+256*28 for base in(TABLE,OTHER_TABLE))]
def cases():
    for field in('count','previous','fallback','current'):
        for byte in range(256):
            y,height,limit=FLOAT_CASES[byte%len(FLOAT_CASES)];v=dict(flags=0 if field=='current'else 8,y=y,height=height,limit=limit,seed=byte&7);v[field]=byte;yield Case(**v)
    for found,flags,count,values,mutation,phase in itertools.product((False,True),(0,8),(0,1,128),FLOAT_CASES,(0,2,7,16),(0,8)):
        y,height,limit=values;yield Case(found=found,flags=flags,count=count,y=y,height=height,limit=limit,mutation=mutation,phase=phase,previous=0,fallback=255,current=128)
    for actor,found,mutation,phase in itertools.product((0,0x10000),(False,True),(0,7),(0,8)):
        yield Case(actor=actor,found=found,mutation=mutation,phase=phase)
