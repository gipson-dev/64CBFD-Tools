"""Connect the two original helpers and retail callback-table caller."""
import itertools,struct
from tools.experiments import game_owner_velocity_150d6cc4_match as match
from tools.tests import game_owner_velocity_150d6cc4_oracle as g
from tools.match_progress import load_elf_functions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def helper_data():
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes()
    live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    code={}
    for entry,name,n in ((g.COPY,'func_150D6C98',11),(g.SCALE,'func_15131958',19)):
        words=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2d4b0)
        assert tuple(live[name])==words
        code.update(zip(range(entry,entry+4*n,4),words))
    return rom,code

class Connected(g.Machine):
    def __init__(self,ws,c,mem,code):
        self.case=c;self.syms={'func_150D6C98':g.COPY,'func_15131958':g.SCALE,'D_800BE9A4':g.DT,'D_800BE9A8':g.ACCEL}
        FactoryOracle.__init__(self,ws,mem,c,entry=g.ENTRY,s=self.syms,connected=code,arguments=(g.OWNER,0x12345678))
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=0
    def hook(self,t):raise AssertionError(('unexpected',hex(t)))

def real_helpers(state):
    rom,code=helper_data();bodies=[g.words(state[x])for x in ('after','retail','generated')];count=0;visited=set()
    for phase,word,identity,factor,count_value,dt,vector in itertools.product((0,8),(0,1),(0,1),
            (0x3f000000,0x3fa00000),(0,1,2),(0x3e800000,0xbe800000),(0,1,2)):
        c=g.Case(phase,word,identity,factor,count_value,dt,0,vector);initial=g.fixture(c)
        expected=g.Machine(bodies[0],c,initial.copy()).run()
        models=[Connected(ws,c,initial.copy(),code).run()for ws in bodies]
        comparable=lambda m:(g.public(m.memory),m.calls,m.r[2],m.fcsr)
        assert all(comparable(m)==comparable(expected)for m in models),c
        visited|=models[0].visits&set(code);count+=1
    assert visited==set(code)
    return {'cases':count,'helper_words':len(code),'visited_helper_words':len(visited)}

class Caller(g.Machine):
    def __init__(self,ws,c,mem,window,code,start,end):
        connected=dict(code);connected.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws))
        self.case=c;self.syms={'func_150D6C98':g.COPY,'func_15131958':g.SCALE,'D_800BE9A4':g.DT,'D_800BE9A8':g.ACCEL}
        FactoryOracle.__init__(self,window,mem,c,entry=start,s=self.syms,connected=connected,arguments=(g.OWNER,))
        self.r[15]=30*4;self.r[7]=0;self.r[29]=g.STACK+c.phase-0x58
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=0
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
    assert struct.unpack_from('>I',rom,0x22e298)[0]==g.ENTRY
    bodies=[g.words(state[x])for x in ('after','retail','generated')];count=0
    for phase,word,identity,count_value,vector in itertools.product((0,8),(0,1),(0,1),(0,1,2),(0,1)):
        c=g.Case(phase,word,identity,0x3f000000,count_value,0x3e800000,0,vector)
        initial=g.fixture(c);g.put(initial,0x800897d8,g.ENTRY);results=[]
        for ws in bodies:
            m=Caller(ws,c,initial.copy(),window,code,start,end)
            try:m.run();raise AssertionError('caller failed to stop')
            except WindowBoundary:pass
            results.append((g.public(m.memory),m.calls,m.r[2],m.fcsr))
        assert results[0]==results[1]==results[2],c;count+=1
    return {'cases':count,'table':'D_80089760[30]','call_pc':'0x15130A38'}
