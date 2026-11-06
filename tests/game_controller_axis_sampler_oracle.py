"""Independent signed countdown/dead-zone/clamp model and literal guest accesses."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments import game_controller_axis_sampler_candidates as source
ENTRY=0x1503F9F0;TABLEPTR=0x800BE728;COUNTDOWN=0x80084484
TABLE,PAD,X,Y=0x20000,0x30000,0x50000,0x50010
MASK=0xffffffff
half=lambda v:((v&65535)^32768)-32768
byte=lambda v:((v&255)^128)-128
def fixture(count=1,slot=0,x=21,y=-21,ox=X,oy=Y,phase=0):
    m={STACK+i:(17*i+0xa5)&255 for i in range(-64,128)}
    for base,n in ((PAD-8,32),(X-8,48),(COUNTDOWN-8,24),(TABLEPTR-8,24)):
        m.update({base+i:(i*29+0x5a)&255 for i in range(n)})
    at=(TABLE+4*half(slot))&MASK
    for i in range(4):m[(at+i)&MASK]=0
    put(m,TABLEPTR,TABLE);put(m,at,PAD);put(m,COUNTDOWN,count,2)
    m[PAD+2]=x&255;m[PAD+3]=y&255
    return m,(slot&MASK,ox,oy),phase
def reference(initial,args,phase):
    m=dict(initial);trace=[]
    def get(p,n):
        v=read(m,p,n);trace.append(('R',p,n,v));return v
    def setv(p,v,n):
        v&=(1<<(8*n))-1;put(m,p,v,n);trace.append(('W',p,n,v))
    slot,ox,oy=args;setv(STACK+phase,slot,4)
    count=half(get(COUNTDOWN,2)-1)
    table=get(TABLEPTR,4);pad=get((table+4*half(slot))&MASK,4)
    if count:
        setv(COUNTDOWN,count,2);setv(ox,0,2);setv(oy,0,2)
    else:
        axis=byte(get(pad+2,1));setv(COUNTDOWN,5,2)
        setv(ox,0 if -20<=axis<=20 else axis,2)
        axis=byte(get(pad+3,1));setv(oy,0 if -20<=axis<=20 else axis,2)
        setv(pad+2,0,1);setv(pad+3,0,1)
        axis=half(get(ox,2));setv(ox,max(-1,min(1,axis)),2)
        axis=half(get(oy,2));setv(oy,max(-1,min(1,axis)),2)
    return m,trace
class AxisOracle(RayOracle):
    def __init__(self,words,memory,args,phase=0,entry=ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
        self.trace=[]
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction:self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.own_instruction and self.recording:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):raise AssertionError(('Unexpected leaf call',hex(t)))

def control_flow(words):
    pending=[0];visited=set();dispatched=set()
    while pending:
        at=pending.pop()
        if at in dispatched:continue
        assert 0<=at<len(words)*4
        dispatched.add(at);visited.add(at);w=words[at//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if w==0x03e00008:visited.add(at+4);continue
        if op in(4,5,20,21):
            options=(True,)if rs==rt and op in(4,20)else(False,)if rs==rt else(True,False)
            if True in options or(op not in(20,21)and False in options):visited.add(at+4)
            if True in options:pending.append(at+4+4*half(w))
            if False in options:pending.append(at+8)
        else:pending.append(at+4)
    return [hex(at)for at in range(0,len(words)*4,4)if at not in visited]
def cases():
    for count,slot,x,y,phase in itertools.product((0,1,2,5,6,0x7fff,0x8000,0x8001,0xffff),
        (0,1,0xffff,0x7fff,0x8000,0x10000,0x1234ffff,0xffff0001,0x80000000,0x7fffffff),(-128,0,127),(-128,0,127),(0,8)):
        yield fixture(count,slot,x,y,phase=phase)
    for value,other,axis in itertools.product(range(256),(-128,-21,-20,0,20,21,127),(0,1)):
        x,y=(value,other)if axis==0 else(other,value)
        yield fixture(1,0,x,y)
    targets=(X,Y,PAD,PAD+2,COUNTDOWN,COUNTDOWN+2,TABLEPTR,TABLEPTR+2,STACK,STACK+4,STACK+8)
    for ox,oy,count in itertools.product(targets,targets,(1,2,0x8000)):
        yield fixture(count,0,127,-128,ox,oy)
