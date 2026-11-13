"""Connect original RNG instructions and both retail direct-call windows."""
import itertools,struct
from tools.experiments import game_random_effect_pair_150d6388_match as match
from tools.tests import game_random_effect_pair_150d6388_oracle as g
from tools.match_progress import load_elf_functions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def helper_data():
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes()
    live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');code={}
    for entry,name,n in ((g.I,'func_150ADA20',18),(g.F,'func_150ADA68',25)):
        words=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2d4b0);assert tuple(live[name])==words
        code.update(zip(range(entry,entry+4*n,4),words))
    return rom,code

def real_rng(state):
    rom,code=helper_data();visited=set();count=0
    for name,seed,phase,selector in itertools.product(g.ENTRIES,g.SEEDS,(0,8),(0,1,127,255)):
        c=g.Case(phase=phase,selector=0x12340000|selector,seed=seed,connected=1)
        initial=g.fixture(c);expected,calls,draws=g.reference(initial,name,c)
        for obj in (state['after'],state['retail'][name],state['generated']):
            m=g.Machine(g.words(obj,name),name,c,initial.copy(),connected=code).run()
            assert(g.public(m.memory),m.calls)==(expected,calls),(name,c,m.calls,calls)
            visited|=m.visits&set(code)
        count+=1
    assert visited==set(code)
    return {'cases':count,'rng_words':len(code),'visited_rng_words':len(visited)}

class Caller(g.Machine):
    def __init__(self,ws,name,c,mem,window,code,start,end):
        connected=dict(code);connected.update(zip(range(g.ENTRIES[name],g.ENTRIES[name]+4*len(ws),4),ws))
        self.case=c;self.name=name;self.draws=[];self.n=self.fi=0;self.home=g.STACK+c.phase-0x220;self.syms=g.symbols()
        FactoryOracle.__init__(self,window,mem,c,entry=start,s=self.syms,connected=connected,arguments=(c.position,c.selector,c.context))
        self.r[20]=c.selector;self.r[21]=c.context;self.r[29]=self.home;self.before=self.r[:]
        self.code[end]=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
    def record_call(self,target):
        if target==g.ENTRIES[self.name]:
            args=tuple(x&g.MASK for x in self.arguments(3))
            assert args==(self.home+0x1b4,self.case.selector&255,self.case.context&g.MASK),args
            self.calls.append((target,args))
        else:super().record_call(target)

def caller(state):
    rom,code=helper_data();windows={'func_150D6434':(0x150d633c,0x150d634c),'func_150D6388':(0x150d634c,0x150d635c)};count=0
    for name,seed,phase,selector in itertools.product(g.ENTRIES,g.SEEDS,(0,8),(0,255)):
        start,end=windows[name];window=struct.unpack_from('>4I',rom,start-0x15000000+0x2d4b0)
        home=g.STACK+phase-0x220;position=home+0x1b4
        c=g.Case(phase=phase,selector=0x12340000|selector,context=0x87654321,seed=seed,connected=1,position=position)
        initial=g.fixture(c);expected,calls,_=g.reference(initial,name,c,home=home);results=[]
        for obj in (state['after'],state['retail'][name],state['generated']):
            m=Caller(g.words(obj,name),name,c,initial.copy(),window,code,start,end)
            try:m.run();raise AssertionError('caller failed to stop')
            except WindowBoundary:pass
            results.append((g.public(m.memory),m.calls))
        expected_calls=[(g.ENTRIES[name],(position,selector,c.context))]+calls
        assert all(x==(expected,expected_calls)for x in results),(name,c)
        count+=1
    return {'cases':count,'caller':'func_150D5A6C','windows':['0x150D633C','0x150D634C']}
