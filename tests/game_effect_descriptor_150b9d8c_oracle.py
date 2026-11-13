"""Guest differential screens, including unqualified stack aliases."""
from dataclasses import dataclass
import itertools
from tools.experiments import game_effect_descriptor_150b9d8c_screen as packet
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x150B9D8C;RNG=0x150ADA20;FACTORY=0x1513C4EC;ACTOR=0x30000
SYMS={'func_150ADA20':RNG,'func_1513C4EC':FACTORY}
@dataclass(frozen=True)
class Case:
    actor:int=ACTOR;phase:int=0;selector:int=-1;randoms:tuple=(0x76543210,0x12345678,0x80000001);mutation:int=0
def fixture(c):
    home=STACK+c.phase;m={home+i:(i*17+0xa5)&255 for i in range(-4096,2048)}
    for i in range(0xc0):m.setdefault(c.actor+i,(i*29+0x5a)&255)
    for off,value in ((0x98,c.selector),(0x9c,100),(0xa0,-200),(0xa2,300),(0xa6,-400)):put(m,c.actor+off,value,2)
    put(m,c.actor+0x90,0x12345678);m[c.actor+0xc]=0xd2;m[c.actor+1]=0xe3
    return m
def words(path):
    t,fs,refs=parse_object(path);f=fs['func_150B9D8C'];a=f['value'];n=f['size'];return bound_blob(t[a:a+n],{i-a:v for i,v in refs.items()if a<=i<a+n},SYMS)
class Machine(FactoryOracle):
    def __init__(self,ws,c,m,connected=None):
        self.c=c;self.home=STACK+c.phase;self.draw=0;self.packets=[]
        super().__init__(ws,m,c,entry=ENTRY,s=SYMS,connected=connected,arguments=(c.actor,));self.before=self.r[:]
    def record_call(self,t):
        if t==RNG:self.calls.append((t,()))
        elif t==FACTORY:
            args=tuple(self.arguments(16));p=args[0];self.calls.append((t,args));self.packets.append(bytes(self.memory[p+i]for i in range(40)))
        else:raise AssertionError(hex(t))
    def hook(self,t):
        if t==RNG:
            value=self.c.randoms[self.draw];self.draw+=1
            if self.c.mutation:
                for offset in (0x9c,0xa0,0xa2,0xa6):put(self.memory,self.c.actor+offset,(self.draw*100+offset)&65535,2)
                self.memory[self.c.actor+0xc]=0x50+self.draw;self.memory[self.c.actor+1]=0x60+self.draw
        else:value=0
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value&0xffffffff


def programs(state):
    values=[words(state[n]) for n in ('four','retail','generated','generic')]
    assert values[1]==values[2]==values[3]
    return values


def ordinary(state):
    all_programs=programs(state);count=0;gaps=(7,22,23,*range(28,40))
    for phase,selector,mutation,draws in itertools.product((0,8),(-32768,-2,-1,0,1,32767),(0,1),((0,0,0),(1,1,1),(0xffffffff,0x12345678,0x80000001))):
        c=Case(ACTOR,phase,selector,draws,mutation);initial=fixture(c);states=[]
        for program in all_programs:
            m=Machine(program,c,initial.copy()).run();states.append((m.calls,m.packets))
        assert states.count(states[0])==4,(c,states)
        calls,packets=states[0]
        if selector!=-1:
            assert not calls and not packets
        else:
            assert [x[0]for x in calls]==[RNG,RNG,RNG,FACTORY] and len(packets)==1
            args=calls[-1][1];p=STACK+phase-0x2c;data=packets[0]
            assert args[:4]==(p,0,2,0) and len(data)==40
            assert int.from_bytes(data[0:4],'big')==0x11 and int.from_bytes(data[4:6],'big')==100 and data[6]==4
            assert data[8:16]==bytes(8) and data[16:22]==bytes((255,0x78,0,0,0,255)) and int.from_bytes(data[24:28],'big')==0x30001
            assert all(data[i]==initial[p+i] for i in gaps)
            assert args[9:14]==(draws[0]&255,((draws[2]&1)<<1)+(draws[1]&1),3,255,0)
            assert args[14:16]==((0x53,0x63)if mutation else (0xd2,0xe3))
        count+=1
    return {'cases':count,'programs':4,'descriptor_bytes':40,'private_gap_bytes':len(gaps)}


def aliases(state):
    all_programs=programs(state)
    c=Case(STACK-0xd0,0,-1,(0x76543210,0x12345678,0x80000001),0);initial=fixture(c);results=[]
    for program in all_programs:
        m=Machine(program,c,initial.copy()).run();results.append((m.calls,m.packets))
    assert results[0]!=results[1] and results[1]==results[2]==results[3]
    second=Case(STACK-0xd8,0,-1,(0x76543210,0x12345678,0x80000001),0);initial=fixture(second);other=[]
    for label in ('two','retail','frame'):
        m=Machine(words(state[label]),second,initial.copy());m.r[16]=m.before[16]=0xffff0000;m.run();other.append((m.calls,m.packets))
    assert other[0]!=other[1] and other[2]!=other[1]
    return {'four_word_alias_diff':True,'two_word_alias_diff':True,'larger_frame_alias_diff':True,
            'raw_arg4':hex(results[0][0][-1][1][4]),'retail_arg4':hex(results[1][0][-1][1][4]),
            'scope':'deliberately overlapping guest actor and callee frame; caller relevance unproven'}
