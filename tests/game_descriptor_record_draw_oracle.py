"""Captured matrix-batch inputs, live pointers, original indirect caller."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_descriptor_record_draw_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,HELPER,GLOBAL=source.ENTRY,0x151137D4,0x800BE9C0
PARENT,OTHER,TABLE,HEADS=0x15188D00,0x151895F4,0x8008D590,0x800DF7C8
DRAW,DRAW2,FIRST,SECOND,MATRIX0,MATRIX1,CURSOR,MARK=0x30000,0x32000,0x40000,0x50000,0x90000,0xA0000,0xB0000,0x80000
u32=lambda x:x&0xFFFFFFFF
sign16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    count:int=3
    stride:int=7
    step:int=127
    frame:int=255
    view:int=0xDEAD8001
    mode:int=0
    phase:int=0
    alias:bool=False
def symbols():return dict(D_800BE9C0=GLOBAL,func_151137D4=HELPER)
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+165)&255 for i in range(-512,1024)}
    for p,n in((DRAW-0x90,0x100),(DRAW2,32),(FIRST,0xB0),(SECOND,0xB0),(MARK,4),(CURSOR,256)):
        m.update({p+i:(i*29+89)&255 for i in range(n)})
    for p in(DRAW,DRAW2):
        m[p]=1;m[p+1]=c.stride;m[p+2]=c.count;m[p+3]=c.step
        put(m,p+8,MATRIX0);put(m,p+12,0);put(m,p+16,DRAW-0x88 if c.alias and p==DRAW else FIRST)
    m[FIRST+0x8A]=0xD7;m[SECOND+0x8A]=0x2D;m[s['D_800BE9C0']]=c.frame;put(m,MARK,0)
    return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+1024}
def effect(m,c,a,n,draw=DRAW,s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;put(m,MARK,n)
    if c.mode&1:put(m,draw+16,SECOND if n&1 else FIRST)
    if c.mode&2:put(m,draw+8,MATRIX1 if n&1 else MATRIX0)
    if c.mode&4:m[draw+1]^=0xFF;m[draw+2]^=0x55;m[draw+3]^=0xAA;m[s['D_800BE9C0']]^=0x7F
    if c.mode&8:m[a[1]+0x8A]^=0xA5
    if c.mode&32:put(m,home+8,0x12347FFF)
    return 0 if c.mode&16 else u32(a[0]+8*(1+n%3))
def reference(initial,c=Case(),arguments=None,s=None,home=None):
    s=symbols()if s is None else s;a=(CURSOR,DRAW,c.view)if arguments is None else arguments
    m=dict(initial);draw=a[1];count=m[draw+2];cursor=a[0];calls=[];observations=[]
    if not count:return m,calls,cursor,observations
    step=m[draw+3];opacity=step*96;current=m[s['D_800BE9C0']]*m[draw+1];saved=m[read(m,draw+16)+0x8A]
    for i in range(count):
        m[read(m,draw+16)+0x8A]=(opacity>>8)&255
        args=(cursor,read(m,draw+16),u32(read(m,draw+8)+(current<<6)),u32(sign16(a[2])),0,0)
        calls.append((s['func_151137D4'],args));observations.append(m[args[1]+0x8A])
        cursor=effect(m,c,args,i+1,draw,s,home);opacity+=step<<5;current+=1
    m[read(m,draw+16)+0x8A]=saved
    return m,calls,cursor,observations
class Oracle(FactoryOracle):
    def __init__(self,w,m,c=Case(),s=None,entry=ENTRY,arguments=None,connected=None):
        self.c=c;self.s=symbols()if s is None else s;self.observations=[];self.active_draw=DRAW;self.target_calls=0
        self.pending_contract=None;self.completed_contracts=0;self.caller_arguments=[]
        super().__init__(w,m,c,entry=entry,s={},arguments=(CURSOR,DRAW,c.view)if arguments is None else arguments,connected=connected)
        self.before_f=self.f[:]
    def execute(self,word):
        if self.pending_contract is not None and self.current_pc==self.contract_return:
            memory,calls,result,obs=self.pending_contract
            assert(public(self.memory,self.c),self.calls[self.contract_calls:],self.r[2],self.observations[self.contract_observations:])==(public(memory,self.c),calls,result,obs)
            self.pending_contract=None;self.completed_contracts+=1
        super().execute(word)
    def record_call(self,t):
        counts={ENTRY:3,OTHER:3,self.s['func_151137D4']:6};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:
            self.active_draw=a[1];self.target_home=self.r[29];self.target_calls=0
            self.caller_arguments.append(a)
            self.pending_contract=reference(self.memory,self.c,a,self.s,self.target_home)
            self.contract_calls=len(self.calls);self.contract_observations=len(self.observations);self.contract_return=self.r[31]
        if t==self.s['func_151137D4']:self.observations.append(self.memory[a[1]+0x8A])
    def hook(self,t):
        if t==OTHER:result=u32(self.calls[-1][1][0]+8)
        else:
            assert t==self.s['func_151137D4'];self.target_calls+=1
            result=effect(self.memory,self.c,self.calls[-1][1],self.target_calls,self.active_draw,self.s,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=result
def payload(obj):
    t,fs,rs=parse_object(obj);f=fs[source.FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:v for p,v in rs.items()if a<=p<a+n}
def bound(obj,s=None):return bound_blob(*payload(obj),symbols()if s is None else s)
def cases():
    for count,view,mode,phase in itertools.product((0,1,2,3,127,128,255),(0,0x7FFF,0x8000,0xABCDFFFF),(0,15,31),(0,8)):
        yield Case(count=count,view=view,mode=mode,phase=phase)
    for i in range(256):yield Case(count=i,stride=i,step=(i*37)&255,frame=(i*73)&255,view=0xABCD0000|i,mode=15)
    for count,mode in itertools.product((0,1,2,127,255),(0,8,15)):yield Case(count=count,mode=mode,alias=True)
    for mode,phase in itertools.product(range(64),(0,8)):yield Case(mode=mode,phase=phase)
def caller_machine(rom,words,c=Case(),nodes=1,other=False,group=0):
    initial=fixture(c);put(initial,HEADS,DRAW if nodes and group==0 else 0);put(initial,HEADS+4,DRAW if nodes and group==1 else 0)
    put(initial,TABLE,OTHER);put(initial,TABLE+4,ENTRY);put(initial,TABLE+8,0);put(initial,TABLE+12,0)
    if nodes==2:put(initial,DRAW+12,DRAW2)
    if other:initial[DRAW]=0
    body=struct.unpack_from('>82I',rom,0x1B61B0);code=dict(zip(range(ENTRY,ENTRY+284,4),words))
    return Oracle(body,initial,c,entry=PARENT,arguments=(CURSOR,group,c.view),connected=code)
def controls():
    b=source.SELECTED
    return dict(wrong_start=b.replace('D_800BE9C0 * draw->stride','draw->stride'),
        wrong_opacity=b.replace('step * 96','step * 64'),wrong_step=b.replace('step << 5','step << 4'),
        wrong_view=b.replace('viewIndex, 0, 0','viewIndex & 255, 0, 0'),
        wrong_saved=b.replace('savedOpacity = draw->descriptor[0x8A]','savedOpacity = draw->descriptor[0x8B]'),
        wrong_restore=b.replace('draw->descriptor[0x8A] = savedOpacity','draw->descriptor[0x8A] = 0'),
        live_count=b.replace('index != count','index < draw->count'),
        false_return=b.replace('return cursor;','return 0;'),
        wrong_matrix=b.replace('(current << 6)','(current << 5)'),
        skip_single=b.replace('if (initialCount == 0)','if (initialCount <= 1)'))
