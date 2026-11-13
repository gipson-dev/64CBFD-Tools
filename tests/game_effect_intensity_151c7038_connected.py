"""Connect the retail helper and callback-table caller window."""
import itertools,struct
from tools.experiments import game_effect_intensity_151c7038_match as match
from tools.tests import game_effect_intensity_151c7038_oracle as d
from tools.match_progress import load_elf_functions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

META=0x50000

def helper_data():
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes()
    offset=d.HELPER-0x15000000+0x2d4b0
    helper=struct.unpack_from('>9I',rom,offset)
    live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    assert tuple(live['func_15142A5C'])==helper
    return rom,dict(zip(range(d.HELPER,d.HELPER+36,4),helper))

class Connected(d.Machine):
    def __init__(self,ws,c,mem,code):
        self.case=c;self.syms={'func_15142A5C':d.HELPER}
        FactoryOracle.__init__(self,ws,mem,c,entry=d.ENTRY,s=self.syms,connected=code,arguments=(d.OWNER,))
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
    def hook(self,target):raise AssertionError(('unexpected call',hex(target)))

def memory(c,half):
    mem=d.fixture(c)
    mem.update({d.EFFECT+i:(i*7+9)&255 for i in range(160,0x2d4)})
    mem.update({META+i:(i*11+3)&255 for i in range(128)})
    d.put(mem,d.EFFECT+0x2d0,META);d.put(mem,META+0x3c,half,2)
    return mem

def real_helper(state):
    rom,code=helper_data();raw=d.words(state['after']);retail=d.words(state['retail']);count=0;visited=set()
    for phase,kind,value,flag,half,fcsr in itertools.product((0,8),(0xe9,0xe8),
            (0,0x3f800000,0x41000000,0xbf800000,0x7fc12345),(0,0xffffffff),
            (0,1,0x7fff,0x8000,0xffff),(0,0xa5a50003)):
        answer=int(0<half<0x8000);c=d.Case(phase,kind,value,flag,answer,0,fcsr);mem=memory(c,half)
        model=d.Machine(raw,c,mem.copy()).run();left=Connected(raw,c,mem.copy(),code).run()
        right=Connected(retail,c,mem.copy(),code).run();visited|=left.visits&set(code)
        compare=lambda m:(d.public(m.memory),m.r[2],m.fcsr)
        assert compare(model)==compare(left)==compare(right),(c,half)
        count+=1
    assert visited==set(code)
    return {'cases':count,'helper_words':len(code),'visited_helper_words':len(visited)}

class Caller(d.Machine):
    def __init__(self,ws,c,mem,window,code,start,end):
        connected=dict(code);connected.update(zip(range(d.ENTRY,d.ENTRY+4*len(ws),4),ws))
        self.case=c;self.syms={'func_15142A5C':d.HELPER}
        FactoryOracle.__init__(self,window,mem,c,entry=start,s=self.syms,connected=connected,arguments=(d.OWNER,))
        self.r[16]=d.OWNER;self.r[2]=23;self.r[5]=0;self.r[29]=d.STACK+c.phase-40
        self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
        self.code[end]=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
    def record_call(self,target):
        if target==d.ENTRY:
            assert self.r[4]==d.OWNER;self.calls.append((target,(d.OWNER,)))
        else:super().record_call(target)
    def hook(self,target):raise AssertionError(('unexpected call',hex(target)))

def caller(state):
    rom,code=helper_data();start,end=0x15132248,0x1513226c
    window=struct.unpack_from('>9I',rom,start-0x15000000+0x2d4b0)
    assert struct.unpack_from('>I',rom,0x22e3cc)[0]==d.ENTRY
    bodies=[d.words(state[x]) for x in ('after','retail','generated')];count=0
    for phase,kind,value,half in itertools.product((0,8),(0xe9,0xe8),
            (0,0x3f800000,0x41000000,0xbf800000,0x7fc12345),(0,1,0xffff)):
        c=d.Case(phase,kind,value,0x12345678,int(0<half<0x8000),0,0);mem=memory(c,half)
        d.put(mem,0x8008990c,d.ENTRY);results=[]
        for body in bodies:
            m=Caller(body,c,mem.copy(),window,code,start,end)
            try:m.run();raise AssertionError('caller window did not stop')
            except WindowBoundary:pass
            results.append((d.public(m.memory),m.r[2],m.fcsr,m.calls))
        assert results[0]==results[1]==results[2],c
        assert results[0][3][0]==(d.ENTRY,(d.OWNER,));count+=1
    return {'cases':count,'table':'D_800898B0[23]','call_pc':'0x15132264'}
