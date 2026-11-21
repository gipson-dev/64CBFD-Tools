"""Independent camera-state memory model and exact-stream guest checks."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,sys
from tools.experiments import game_camera_script_state_15125c40_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_camera_state_15125924_direct_oracle import Machine as PriorMachine
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15125C40;HELPER=0x1509BFB0;GLOBAL=0x800D1940;CAMERA=0x30000;ACTOR=0x50000;FLAGS=0x60000;MARK=0x70000
SYMS={'func_1509BFB0':HELPER,'D_800D1940':GLOBAL}
@dataclass(frozen=True)
class Case:
    phase:int=0;category:int=0;state:int=0;timer:int=1;flags:int=0;mutation:int=0;value:float=12.75;alias:int=0
def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
    for base,n in((CAMERA,0x900),(ACTOR,0x200),(FLAGS,32),(MARK,16)):m.update({base+i:(i*29+0x35)&255 for i in range(n)})
    pointer=(FLAGS,CAMERA+0x36A,CAMERA+0x5F0,CAMERA+0x7CC)[c.alias]
    for at,v in((0x7CC,c.timer),(0x5F0,c.flags),(0x3D0,ACTOR),(0x36C,pointer)):put(m,CAMERA+at,v)
    m[GLOBAL]=c.category;m[CAMERA+0x23E]=c.state;put(m,CAMERA+0x36A,0xA581,2);put(m,FLAGS,0xA581,2)
    put(m,ACTOR+0x40,bits(c.value));put(m,MARK,0);return m
def effect(m,c,count):
    put(m,MARK,count)
    if c.mutation:
        put(m,CAMERA+0x5F0,0xC1000000|count)
        m[CAMERA+0x23E]^=0x55;m[GLOBAL]^=0x55
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+512}
def reference(initial,c):
    m=dict(initial);calls=[];state=m[CAMERA+0x23E];special=m[GLOBAL]==0x42 and state==0x1A
    active=state in(3,0x1A)or special
    timer=(read(m,CAMERA+0x7CC)-1)&0xFFFFFFFF;put(m,CAMERA+0x7CC,timer)
    def call(args):calls.append((HELPER,tuple(x&0xFFFFFFFF for x in args)));effect(m,c,len(calls))
    if active:
        if timer==0:
            if special:call((3,0x9000,0x18,math.trunc(floating(read(m,read(m,CAMERA+0x3D0)+0x40))),0,250))
            elif state==0x1A:call((3,0x9000,0x18,0,0,250))
            put(m,CAMERA+0x5F0,read(m,CAMERA+0x5F0)|2)
            p=read(m,CAMERA+0x36C);put(m,p,read(m,p,2)|0x10,2)
            flags=read(m,CAMERA+0x36A,2);put(m,CAMERA+0x7CC,1);put(m,CAMERA+0x36A,flags|0x10,2)
    else:
        if read(m,CAMERA+0x5F0)&2:
            call((1,0x9000,0x10,0));call((1,0x9000,0xF,0))
            put(m,CAMERA+0x5F0,read(m,CAMERA+0x5F0)&~2)
        put(m,CAMERA+0x7CC,2)
    return public(m,c),calls
class Machine(PriorMachine):
    def __init__(self,words,c,m):
        self.c=c
        FactoryOracle.__init__(self,words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,))
        self.visited_words=set()
    def execute(self,w):
        if ENTRY<=self.current_pc<ENTRY+372:self.visited_words.add((self.current_pc-ENTRY)//4)
        if w>>26==0 and w&63==0x26:
            self.r[w>>11&31]=(self.r[w>>21&31]^self.r[w>>16&31])&0xFFFFFFFF;self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        assert t==HELPER
        count=self.r[4]+3;assert count in(4,6)
        self.calls.append((t,tuple(self.arguments(count))));self.events.append(('CALL',t,self.calls[-1][1]))
    def hook(self,t):
        assert t==HELPER;effect(self.memory,self.c,sum(target==HELPER for target,_ in self.calls))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs():
    return[bound_blob(*payload(p,'func_15125C40'),SYMS)for p in(out/'image-qualification/retail.o',out/'variant-s32-first/candidate.o',out/'image-qualification/padded.o')]
def corpus():
    selectors=[(v,s)for v in range(256)for s in(0,3,26)]+[(v,s)for v in(0,0x42)for s in range(256)]
    for category,state in selectors:
        for timer,flags,mutation in itertools.product((0,1,2,0x80000000),(0,2),(0,1)):
            yield Case(category=category,state=state,timer=timer,flags=flags,mutation=mutation)
    for phase,category,state,timer,flags,mutation,value,alias in itertools.product(
        (0,8),(0,0x42),(0,3,26),(1,2),(0,2),(0,1),(-12.75,0.,12.75),(0,1,2,3)):
        yield Case(phase,category,state,timer,flags,mutation,value,alias)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def run():
    streams=programs();assert streams[0]==streams[1]==streams[2]
    count=0;coverage=set();examples=[]
    for c in corpus():
        initial=fixture(c);expected=reference(initial,c);results=[]
        for words in streams:
            m=Machine(words,c,dict(initial)).run();assert(public(m.memory,c),m.calls)==expected,c
            results.append(state(m));coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+372)
            assert m.r[29]==STACK+c.phase
        assert results[0]==results[1]==results[2],c
        count+=1
        if c.category in(0,0x42)and c.state in(0,3,26)and c.timer==1 and c.mutation==0 and len(examples)<30:examples.append(c)
    assert coverage==set(range(93)),sorted(set(range(93))-coverage)
    controls={24:0x9205023F,96:0x25F8FFFE,228:0x358D0004,304:0x24070001}
    rejected=[]
    for offset,replacement in controls.items():
        changed=list(streams[0]);assert changed[offset//4]!=replacement;changed[offset//4]=replacement
        failures=0
        for c in examples:
            initial=fixture(c)
            try:
                m=Machine(changed,c,dict(initial)).run();failures+=(public(m.memory,c),m.calls)!=reference(initial,c)
            except(AssertionError,KeyError):failures+=1
        assert failures,offset;rejected.append({'offset':offset,'failing_cases':failures})
    r={'cases_per_stream':count,'streams':3,'word_identity':True,'covered_words':len(coverage),'controls':rejected,
       'private_frame_and_incoming_bytes_equal':True,'full_public_memory_and_ordered_trace_equal':True,
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
