"""Guest differential checks for the private effect-intensity candidate."""
import itertools
from dataclasses import dataclass
from tools.experiments import game_effect_intensity_151c7038_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_actor_intensity_byte_oracle import Oracle as FloatOracle
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put

ENTRY=0x151C7038; HELPER=0x15142A5C; OWNER=0x30000; EFFECT=0x40000; ALT=0x41000
VALUES=(0,0x80000000,0x3f800000,0x40e92492,0x41100000,0xbf800000,
        0x7f7fffff,0x7f800000,0xff800000,0x7fc12345)
@dataclass(frozen=True)
class Case:
    phase:int; kind:int; value:int; flag:int; answer:int; mutation:int; fcsr:int

def words(obj):
    raw,refs=match.payload(obj)
    return bound_blob(raw,refs,{'func_15142A5C':HELPER})

def fixture(c):
    memory={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
    for base,n in ((OWNER,256),(EFFECT,160),(ALT,160)):
        memory.update({base+i:(i*29+0x59)&255 for i in range(n)})
    put(memory,OWNER+0x7c,EFFECT);put(memory,OWNER+0x60,c.flag)
    put(memory,EFFECT+0x84,c.kind,2);put(memory,EFFECT+0x4c,c.value)
    return memory

def public(memory):
    return {a:b for a,b in memory.items() if not STACK-512<=a<STACK+512}

def external_trace(machine):
    return [e for e in machine.trace if not STACK-512<=e[1]<STACK+512]

class Machine(FloatOracle):
    def __init__(self,ws,c,mem):
        self.case=c;self.syms={'func_15142A5C':HELPER}
        FactoryOracle.__init__(self,ws,mem,c,entry=ENTRY,s=self.syms,arguments=(OWNER,))
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
    def record_call(self,target):
        assert target==HELPER
        args=tuple(self.arguments(1));assert args==(EFFECT,)
        self.calls.append((target,args))
    def hook(self,target):
        assert target==HELPER
        c=self.case
        if c.mutation&1:
            put(self.memory,EFFECT+0x4c,0x40000000);put(self.memory,EFFECT+0x84,0x1234,2)
        if c.mutation&2:
            put(self.memory,OWNER+0x60,0x80705030);put(self.memory,OWNER+0x7c,ALT)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=c.answer

def run(state):
    raw=words(state['after']);retail=words(state['retail']);padded=words(state['generated'])
    assert padded==retail
    count=0
    for args in itertools.product((0,8),(0xe9,0xe8),VALUES,(0,0xffffffff),
                                  (0,1),(0,1,2,3),(0,0xa5a50003)):
        c=Case(*args);initial=fixture(c)
        machines=[Machine(ws,c,initial.copy()).run() for ws in (raw,retail,padded)]
        results=[(public(m.memory),m.calls,m.r[2],m.fcsr,external_trace(m)) for m in machines]
        assert results[0]==results[1]==results[2],c
        assert all(m.fcsr==c.fcsr for m in machines),c
        count+=1
    return {'cases':count,'bodies':3,'helper':'modeled with table/field mutations',
            'fcsr':'modeled restoration; not hardware exception proof'}
