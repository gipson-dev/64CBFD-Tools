"""Signed keyed-list updates, allocation rollback and byte-accurate node state."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_keyed_buffer_registration_candidates as source
from tools.tests.game_table_payload_spawn_oracle import Oracle as InstructionOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import signed
NODES,OTHER,NEW,BUFFER=0x30000,0x38000,0x60000,0x50000
HEAD,ALLOC,FREE,ZERO,APPEND,CORE=0x800DF7CC,0x10003C40,0x10004074,0x100226F0,0x15188A58,0x10003C6C
SYMS=dict(D_800DF7CC=HEAD,allocate_memory=ALLOC,func_10004074=FREE,bzero=ZERO,func_15188A58=APPEND)
TIMERS=(-0x80000000,-32769,-32768,-1,0,32767,32768,65535,0x7FFFFFFF)

@dataclass(frozen=True)
class Case:
    count:int=0
    match:int=-1
    old:int=-1
    timer:int=32768
    mode:int=0xFFFFFF80
    outcome:int=2
    mutation:int=0
    phase:int=0
    residue:int=0
    key:int=0x81234567
    node:int=NEW
    buffer:int=0

def buffer(c):return c.buffer if c.buffer else BUFFER+c.residue
def signed16(v):return((v&65535)^32768)-32768
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}

def fixture(c=Case(),s=SYMS):
    m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    for p,n in((NODES,512),(OTHER,32),(c.node,512),(buffer(c)-16,432),(s['D_800DF7CC']-4,12)):
        m.update({p+i:(i*13+89)&255 for i in range(n)})
    for i in range(4):
        p=NODES+32*i;key=c.key if i==c.match or c.match==4 and i in(0,2)else(c.key^0x1010000)+i
        put(m,p+16,key&0xFFFFFFFF);put(m,p+12,NODES+32*(i+1)if i+1<c.count else 0);put(m,p+6,c.old&65535,2)
    put(m,OTHER+12,0);put(m,OTHER+16,c.key^0x55550000)
    put(m,s['D_800DF7CC'],NODES if c.count else 0)
    return m

def effect(m,c,s,stage,home):
    if stage==0 and c.mutation&1:
        put(m,OTHER+12,read(m,s['D_800DF7CC']));put(m,s['D_800DF7CC'],OTHER)
    if stage==1 and c.mutation&2:
        m[c.node+5]=0xED
        for i in range(384):m[buffer(c)+i]=0xD3
    if stage==2 and c.mutation&4:
        m[c.node+4]=0xAB;put(m,c.node+6,0x8123,2)
    if stage==0 and c.mutation&8:
        put(m,home+36,0x8123CD34);put(m,home+40,0xFFFFFF80)

def append(m,node,head):
    put(m,node+12,0);p=read(m,head)
    if not p:put(m,head,node);return
    seen=set()
    while read(m,p+12):
        if p in seen:raise AssertionError('Cyclic registration reference list')
        seen.add(p);p=read(m,p+12)
    put(m,p+12,node)

def reference(initial,c=Case(),s=SYMS,home=None,saved=None):
    m=dict(initial);home=STACK+c.phase-32 if home is None else home
    # Save values come from the caller's real callee-saved register fixture.
    saved=saved or {16:0xA0000010,17:0xA0000011,31:0xDEAD0000}
    for off,r in((20,16),(24,17),(28,31)):put(m,home+off,saved[r])
    put(m,home+36,c.timer&0xFFFFFFFF);put(m,home+40,c.mode&0xFFFFFFFF)
    p=read(m,s['D_800DF7CC']);match_timer=signed(read(m,home+36));calls=[]
    while p:
        if read(m,p+16)==(c.key&0xFFFFFFFF):
            if signed16(read(m,p+6,2))<match_timer:put(m,p+6,match_timer&65535,2)
            m[p+4]=read(m,home+40)&255;return m,calls
        p=read(m,p+12)
    def call(t,args,stage=None):
        calls.append((t,tuple(args)))
        if stage is not None:effect(m,c,s,stage,home)
        for i in range(4):put(m,home+4*i,0xB5000000+i)
    call(s['allocate_memory'],(20,1,0,0),0)
    if c.outcome==0:return m,calls
    call(s['allocate_memory'],(384,1,1,0),1)
    if c.outcome==1:call(s['func_10004074'],(c.node,));return m,calls
    for off,v in((0,1),(1,3),(2,0),(3,20)):m[c.node+off]=v
    mode=read(m,home+40);m[c.node+4]=mode&255;timer=read(m,home+36)
    put(m,c.node+8,buffer(c));put(m,c.node+16,c.key&0xFFFFFFFF);put(m,c.node+6,timer&65535,2)
    calls.append((s['bzero'],(buffer(c),384)))
    for i in range(384):m[buffer(c)+i]=0
    effect(m,c,s,2,home)
    for i in range(4):put(m,home+4*i,0xB5000000+i)
    calls.append((s['func_15188A58'],(c.node,s['D_800DF7CC'])));append(m,c.node,s['D_800DF7CC'])
    for i in range(4):put(m,home+4*i,0xB5000000+i)
    return m,calls

class Oracle(InstructionOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None):
        self.c,self.s=c,s;self.allocations=0;self.home=STACK+c.phase-32;self.before_f=None
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.key&0xFFFFFFFF,c.timer&0xFFFFFFFF,c.mode&0xFFFFFFFF),connected=connected)
        self.before_f=self.f[:]
    def record_call(self,t):
        counts={source.ENTRY:3,self.s['allocate_memory']:4,self.s['func_10004074']:1,self.s['bzero']:2,self.s['func_15188A58']:2,CORE:5}
        if t not in counts:raise AssertionError(('Unbounded registration provider',hex(t)))
        args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        a=self.calls[-1][1];value=0xDEADBEEF
        if t in(self.s['allocate_memory'],CORE):
            stage=self.allocations;self.allocations+=1;effect(self.memory,self.c,self.s,stage,self.home)
            value=(self.c.node if self.c.outcome else 0)if stage==0 else(buffer(self.c)if self.c.outcome==2 else 0)
        elif t==self.s['func_10004074']:assert a==(self.c.node,)
        elif t==self.s['bzero']:
            for i in range(a[1]):self.put(a[0]+i,0,1)
            effect(self.memory,self.c,self.s,2,self.home)
        elif t==self.s['func_15188A58']:append(self.memory,*a)
        else:raise AssertionError(('Unowned registration provider',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value&0xFFFFFFFF

def cases():
    for match,old,timer,mode,phase in itertools.product((0,2,4),(-32768,-1,0,1,32767),TIMERS,(0,255,0xFFFFFF80,0xA5A5007F),(0,8)):
        yield Case(4,match,old,timer,mode,phase=phase)
    for count,outcome,mutation,phase,residue in itertools.product((0,1,4),range(3),(0,7,8,15),(0,8),(0,1,3)):
        yield Case(count,-1,outcome=outcome,mutation=mutation,phase=phase,residue=residue)
    for byte,match in itertools.product(range(256),(-1,0)):
        yield Case(1,match,timer=65535,mode=0xA5A50000|byte,phase=8*(byte&1))
    for key,match in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(-1,0,4)):
        yield Case(4,match,timer=-1,mode=255,key=key)

def controls():
    b=source.SELECTED
    rows={
        'unsigned_timer':('node->timer < timer','(u16)node->timer < (u32)timer'),
        'narrow_incoming_timer':('node->timer < timer','node->timer < (s16)timer'),
        'decrease_timer':('node->timer < timer','1'),
        'ignore_match':('key == node->key','0'),
        'wrong_mode_byte':('node->mode = mode','node->mode = mode >> 8'),
        'missing_rollback':('        func_10004074(node);\n',''),
        'wrong_buffer_size':('allocate_memory(0x180','allocate_memory(0x17C'),
        'short_clear':('bzero(buffer, 0x180)','bzero(buffer, 0x17F)'),
        'clear_retained_byte':('    node->recordSize = 20;','    node->recordSize = 20;\n    node->retained05 = 0;'),
        'wrong_append_head':('(ListNode15188A58 *)&D_800DF7CC','(ListNode15188A58 *)&node')}
    result={n:b.replace(a,z)for n,(a,z)in rows.items()}
    if any(v==b for v in result.values()):raise ValueError('Ineffective registration control')
    return result
