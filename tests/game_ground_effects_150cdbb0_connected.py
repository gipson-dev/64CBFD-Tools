"""Actual RNG and caller windows, with bounded guest access prefixes."""
import itertools
import struct

from tools.experiments import game_ground_effects_150cdbb0_match as packet
from tools.match_progress import load_elf_functions
from tools.tests import game_ground_effects_150cdbb0_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.tests.test_game_random_selector_outputs_match import next_seed, SEEDS

SEED=0x800885B0
START=0x15171C80
END=0x15171C88


class RealRng(RngInstructions):
    def __init__(self,ws,c,mem,code):
        self.c=c;self.home=g.STACK+c.phase;self.point=self.home-12;self.result=self.home-48;self.rng=0
        FactoryOracle.__init__(self,ws,mem,c,entry=g.ENTRY,s=g.SYMS,connected=code,arguments=(c.actor,c.flags,c.third));self.before=self.r[:]
    record_call=g.Machine.record_call
    hook=g.Machine.hook
    def execute(self,w):
        super().execute(w)
        if w>>26==17 and (w>>21&31)==0:
            self.r[w>>16&31]=self.f[w>>11&31]&0xFFFFFFFF;self.r[0]=0


def connected_rng(state):
    rom=(packet.ROOT/'conker/conker.us.bin').read_bytes()
    rng=struct.unpack_from('>18I',rom,g.RNG-0x15000000+0x2D4B0)
    live,_,_=load_elf_functions(str(packet.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    assert tuple(live['func_150ADA20'])==rng
    code=dict(zip(range(g.RNG,g.RNG+4*len(rng),4),rng));count=0;visited=set()
    for seed,phase,hit,flag in itertools.product(SEEDS,(0,8),(0,1),(0,0xFF)):
        one=next_seed(seed);two=next_seed(one)
        c=g.Case(g.ACTOR,flag,0,phase,hit,0,(one&0xFFFFFFFF,two&0xFFFFFFFF))
        initial=g.fixture(c);g.put(initial,SEED,seed,8);expected,calls=g.reference(initial,c)
        if hit:g.put(expected,SEED,two,8)
        for ws in g.programs(state):
            m=RealRng(ws,c,initial.copy(),code).run()
            assert (g.public(m.memory,c),m.calls)==(expected,calls),(c,m.calls,calls)
            visited|=m.visits&set(code)
        count+=1
    assert visited==set(code),(len(visited),len(code))
    return {'cases':count,'rng_words':len(code),'visited_rng_words':len(visited)}


class Caller(g.Machine):
    def __init__(self,window,ws,c,mem):
        self.c=c;self.home=g.STACK+c.phase;self.point=self.home-12;self.result=self.home-48;self.rng=0
        connected=dict(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));connected[END]=0
        FactoryOracle.__init__(self,window,mem,c,entry=START,s=g.SYMS,connected=connected,arguments=(c.actor,c.flags,0))
        self.before=self.r[:];self.code=WindowCode(self.code,self);self.code.ends=(END,)
    def record_call(self,t):
        if t==g.ENTRY:self.calls.append((t,tuple(self.r[4:7])))
        else:super().record_call(t)


def caller(state):
    rom=(packet.ROOT/'conker/conker.us.bin').read_bytes()
    window=struct.unpack_from('>2I',rom,START-0x15000000+0x2D4B0)
    assert window==(0x0D4336EC,0x24060001)
    count=0
    for actor,flag,phase,hit,mutation in itertools.product((0,g.ACTOR),(0,0x12345680,0xFFFFFFFF),(0,8),(0,1),(0,3,7)):
        c=g.Case(actor,flag,1,phase,hit,mutation,(15,0xFFFFFFFF));initial=g.fixture(c);expected,calls=g.reference(initial,c)
        for ws in g.programs(state):
            m=Caller(window,ws,c,initial.copy())
            try:m.run();raise AssertionError('caller escaped')
            except WindowBoundary:pass
            assert (g.public(m.memory,c),m.calls)==(expected,[(g.ENTRY,(c.actor,c.flags,1))]+calls),(c,m.calls,calls)
            assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24]
        count+=1
    return {'cases':count,'caller':'func_15171BF4','window':'0x15171C80..0x15171C88'}


def faults(state):
    programs=g.programs(state);cuts=0
    for hit,mutation in itertools.product((0,1),(0,3,7)):
        c=g.Case(hit=hit,mutation=mutation);initial=g.fixture(c)
        full=g.Machine(programs[1],c,initial.copy()).run()
        for cut in range(full.all_accesses):
            states=[]
            for ws in programs:
                m=g.Machine(ws,c,initial.copy());m.cut=cut
                try:m.run();raise AssertionError(('missing cut',cut))
                except AccessBoundary:pass
                states.append((m.memory,m.calls,m.trace))
            assert states.count(states[0])==4,(c,cut)
            cuts+=1
    return {'cases':6,'access_cuts':cuts,'scope':'guest observable memory/call prefixes; raw call delay may differ'}
