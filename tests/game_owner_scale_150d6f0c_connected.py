"""Connect original helper instructions and the retail callback-table caller."""
import itertools,struct
from tools.experiments import game_owner_scale_150d6f0c_match as match
from tools.tests import game_owner_scale_150d6f0c_oracle as g
from tools.match_progress import load_elf_functions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def helper_data():
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes()
    words=struct.unpack_from('>11I',rom,g.HELPER-0x15000000+0x2d4b0)
    live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    assert tuple(live['func_150D6C98'])==words
    return rom,dict(zip(range(g.HELPER,g.HELPER+44,4),words))

class Connected(g.Machine):
    def __init__(self,ws,c,mem,code):
        self.case=c;self.syms={'func_150D6C98':g.HELPER,'D_800BE9A4':g.DELTA}
        FactoryOracle.__init__(self,ws,mem,c,entry=g.ENTRY,s=self.syms,connected=code,arguments=(g.OWNER,0x12345678))
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
    def hook(self,t):raise AssertionError(('unexpected',hex(t)))

def real_helper(state):
    rom,code=helper_data();bodies=[g.words(state[x]) for x in ('after','retail','generated')]
    count=0;visited=set()
    for phase,word,identity,elapsed,alpha in itertools.product((0,8),(0,1),(0,1),
            (0,0x3f800000,0x40800000,0xbf800000,0x7fc12345),(0x42c80000,0xbf800000)):
        c=g.Case(phase,word,identity,elapsed,alpha,0x3f800000,0,0);initial=g.fixture(c)
        expected=g.Machine(bodies[0],c,initial.copy()).run()
        models=[Connected(ws,c,initial.copy(),code).run()for ws in bodies]
        comparable=lambda m:(g.public(m.memory),m.calls,m.r[2],m.fcsr)
        assert all(comparable(m)==comparable(expected) for m in models),c
        visited|=models[0].visits&set(code);count+=1
    assert visited==set(code)
    return {'cases':count,'helper_words':len(code),'visited_helper_words':len(visited)}

class Caller(g.Machine):
    def __init__(self,ws,c,mem,window,code,start,end):
        connected=dict(code);connected.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws))
        self.case=c;self.syms={'func_150D6C98':g.HELPER,'D_800BE9A4':g.DELTA}
        FactoryOracle.__init__(self,window,mem,c,entry=start,s=self.syms,connected=connected,arguments=(g.OWNER,))
        self.r[15]=31*4;self.r[7]=0;self.r[29]=g.STACK+c.phase-0x58
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
        self.code[end]=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
    def record_call(self,target):
        if target==g.ENTRY:
            assert self.r[4]==g.OWNER and self.r[5]==self.r[29]+0x48
            self.calls.append((target,(self.r[4],self.r[5])))
        else:super().record_call(target)
    def hook(self,t):raise AssertionError(('unexpected',hex(t)))

def caller(state):
    rom,code=helper_data();start,end=0x15130a24,0x15130a40
    window=struct.unpack_from('>7I',rom,start-0x15000000+0x2d4b0)
    assert struct.unpack_from('>I',rom,0x22e29c)[0]==g.ENTRY
    bodies=[g.words(state[x])for x in ('after','retail','generated')];count=0
    for phase,word,identity,elapsed in itertools.product((0,8),(0,1),(0,1),
            (0,0x3f800000,0xbf800000,0x7fc12345)):
        c=g.Case(phase,word,identity,elapsed,0x42c80000,0x3f800000,0,0)
        initial=g.fixture(c);g.put(initial,0x800897dc,g.ENTRY);results=[]
        for ws in bodies:
            m=Caller(ws,c,initial.copy(),window,code,start,end)
            try:m.run();raise AssertionError('caller failed to stop')
            except WindowBoundary:pass
            results.append((g.public(m.memory),m.calls,m.r[2],m.fcsr))
        assert results[0]==results[1]==results[2],c;count+=1
    return {'cases':count,'table':'D_80089760[31]','call_pc':'0x15130A38'}
