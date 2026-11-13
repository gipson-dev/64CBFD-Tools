"""Modeled actor, height-query, and effect-factory behavior."""
import itertools
from dataclasses import dataclass
from tools.experiments import game_ground_effects_150cdbb0_match as packet
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
ENTRY=0x150CDBB0;INIT=0x1504715C;QUERY=0x15046C80;RNG=0x150ADA20;EFFECT=0x1514C678;CONST=0x800A07B0;ACTOR=0x30000
SYMS={'func_1504715C':INIT,'func_15046C80':QUERY,'func_150ADA20':RNG,'func_1514C678':EFFECT,'D_800A07B0':CONST}
u32=lambda x:x&0xffffffff
@dataclass(frozen=True)
class Case:
    actor:int=ACTOR; flags:int=0x123456a5; third:int=0x87654321; phase:int=0; hit:int=1; mutation:int=0; randoms:tuple=(0xffffffff,42)
def fixture(c):
    home=STACK+c.phase;m={home+i:(i*17+0xa5)&255 for i in range(-2048,2048)}
    for i in range(96):m.setdefault(c.actor+i,(i*29+0x5a)&255)
    for i,value in enumerate((1.25,4.5,-3.0)):put(m,c.actor+0x14+4*i,bits(value))
    put(m,CONST,bits(50.0));return m
def public(m,c):
    home=STACK+c.phase
    return {a:b for a,b in m.items() if not home-2048<=a<home+2048}
def adjust(m,c,stage,point,result,home):
    if stage==0 and c.mutation&1:
        for i,v in enumerate((7.0,-3.0,11.0)):put(m,c.actor+0x14+4*i,bits(v))
        put(m,CONST,bits(75.0))
    if stage==1:
        put(m,result,bits(12.5))
        if c.mutation&2:
            put(m,point,bits(21.0));put(m,point+8,bits(-19.0));m[home+7]=0x81
    if stage in (2,3,4) and c.mutation&4:
        put(m,point,bits(30.0+stage));put(m,point+8,bits(-30.0-stage));m[home+7]=(0xa0+stage)&255
def reference(initial,c):
    m=dict(initial);home=STACK+c.phase;point=home-12;result=home-48;put(m,home+4,c.flags);put(m,home+8,c.third);calls=[]
    def clobber():
        for i in range(4):put(m,home-0x78+4*i,0xb5000000+i)
    if not c.actor:return public(m,c),calls
    calls.append((INIT,(result,c.actor)));adjust(m,c,0,point,result,home);clobber()
    put(m,point,read(m,c.actor+0x14));put(m,point+4,bits(floating(read(m,c.actor+0x18))+1000.0));put(m,point+8,read(m,c.actor+0x1c))
    query=(point,0,bits(floating(read(m,c.actor+0x18))-floating(read(m,CONST))),result)
    calls.append((QUERY,query,tuple(read(m,point+4*i)for i in range(3))));adjust(m,c,1,point,result,home);clobber()
    if not c.hit:return public(m,c),calls
    put(m,point+4,read(m,result));calls.append((RNG,()));adjust(m,c,2,point,result,home);clobber()
    calls.append((EFFECT,(read(m,point),read(m,point+4),read(m,point+8),bits(251.0),0,255,(c.randoms[0]&15)+35,0x17,0,bits(0),0,read(m,home+7,1))))
    adjust(m,c,3,point,result,home);clobber();calls.append((RNG,()));adjust(m,c,4,point,result,home);clobber()
    calls.append((EFFECT,(read(m,point),read(m,point+4),read(m,point+8),bits(290.0),0,255,(c.randoms[1]%21)+30,0x18,0,bits(0),0,read(m,home+7,1))))
    return public(m,c),calls
def words(obj,symbols=SYMS):
    t,fs,refs=parse_object(obj);f=fs['func_150CDBB0'];a=f['value'];n=f['size'];return bound_blob(t[a:a+n],{i-a:r for i,r in refs.items()if a<=i<a+n},symbols)
class Machine(FactoryOracle):
    def __init__(self,ws,c,mem,connected=None,entry=ENTRY):
        self.c=c;self.home=STACK+c.phase;self.point=self.home-12;self.result=self.home-48;self.rng=0
        super().__init__(ws,mem,c,entry=entry,s=SYMS,connected=connected,arguments=(c.actor,c.flags,c.third));self.before=self.r[:]
    def record_call(self,t):
        if t==INIT:args=tuple(self.r[4:6]);self.calls.append((t,args))
        elif t==QUERY:
            args=tuple(self.r[4:8]);self.calls.append((t,args,tuple(read(self.memory,args[0]+4*i)for i in range(3))))
        elif t==RNG:self.calls.append((t,()))
        elif t==EFFECT:
            args=(self.f[12],self.f[14],self.r[6],self.r[7],*(read(self.memory,self.r[29]+i*4)for i in range(4,12)));self.calls.append((t,args))
        else:raise AssertionError(('unexpected helper',hex(t)))
    def hook(self,t):
        if t==INIT:stage=0;value=0
        elif t==QUERY:stage=1;value=self.c.hit
        elif t==RNG:stage=2+2*self.rng;value=self.c.randoms[self.rng];self.rng+=1
        else:assert t==EFFECT;stage=3 if self.rng==1 else 5;value=0
        adjust(self.memory,self.c,stage,self.point,self.result,self.home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def programs(state):
    return [words(state[n]) for n in ('after','retail','generated','generic')]

def run(state):
    programs_list=programs(state);assert programs_list[1]==programs_list[2]==programs_list[3]
    count=0;visited=set()
    for phase,actor_kind,flag,hit,mutation,randoms in itertools.product((0,8),(0,1,2,3),(0,0x12345680,0xffffffff),(0,1,0x80000000),range(8),((0,0),(15,20),(0xffffffff,0xffffffff))):
        actor=(0,ACTOR,STACK+phase-0x44,STACK+phase-0x80)[actor_kind]
        c=Case(actor,flag,0x87654321,phase,hit,mutation,randoms);initial=fixture(c);expected=reference(initial,c);states=[]
        for ws in programs_list:
            m=Machine(ws,c,initial.copy()).run();states.append((public(m.memory,c),m.calls));visited.update(m.visits)
        assert all(x==expected for x in states),(c,states,expected)
        count+=1
    result={'cases':count,'programs':4,'retail_words_visited':len(visited),'helper_mutations':True,'aliased_actor_case':True}
    return result
