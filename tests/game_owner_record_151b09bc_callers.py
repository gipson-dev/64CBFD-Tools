"""Original pair-emitter callers with preceding emitter modeled and real memcpy."""
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_owner_record_151b09bc_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
GLOBAL,PREVIOUS=0x800D154C,0x151B01B8
PARENTS=((0x15194794,14,False),(0x15195650,18,True),(0x1507003C,18,True))

def prior_effect(m,c):
    if c.route==1:return
    m[g.A+0x3B]^=0x19
    if c.mutation&16 and not c.source_null:m[g.source_pointer(c)+4]=0x53

class Caller(g.Oracle):
    def __init__(self,words,initial,c,entry,parent,remap):
        code=dict(g.copy_code());code.update({g.ENTRY+4*i:w for i,w in enumerate(words)})
        if remap:initial=g.exchange(initial,g.STACK+c.phase-32)
        arguments=(0 if c.route==1 else g.A,0 if c.source_null else g.source_pointer(c),0xBAD00006)
        FactoryOracle.__init__(self,parent,initial,c,entry=entry,s={},arguments=arguments,connected=code)
        self.service=g.Service(self.memory,c,g.STACK+c.phase-32);self.target_calls=[];self.previous_calls=[]
        self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
    def record_call(self,target):
        owner=0 if self.case.route==1 else g.A;source=0 if self.case.source_null else g.source_pointer(self.case)
        if target==PREVIOUS:
            args=tuple(self.arguments(2));assert args==(owner,source);self.previous_calls.append(args)
        elif target==g.ENTRY:
            args=tuple(self.arguments(5));assert args==(owner,source,1000,255,0),('constructor caller ABI',args)
            self.target_calls.append(args)
        else:super().record_call(target)
    def hook(self,target):
        if target!=PREVIOUS:return super().hook(target)
        prior_effect(self.memory,self.case)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xE5000099

def cases():
    for seed,kind,category,outcome,mutation,phase in itertools.product((0,197),(4,99),(0,1,2),(0,1),(0,31),(0,8)):
        yield g.Case(seed=seed,kind=kind,category=category,outcome=outcome,mutation=mutation,phase=phase,
                     duration=1000,channel=255,context=0,alias=int(seed==0),out_alias=int(seed==197))
    for outcome,mutation,phase in itertools.product((0,1),(0,31),(0,8)):
        yield g.Case(route=1,outcome=outcome,mutation=mutation,phase=phase,duration=1000,channel=255,context=0)

def run(programs):
    rom=(g.recovery.FROZEN/'conker/conker.us.bin').read_bytes();reports=[];controls=[]
    for entry,n,complete in PARENTS:
        parent=list(struct.unpack_from('>'+str(n)+'I',rom,entry-0x14FD2B50));assert parent[0]==0x27BDFFE0
        jal=[i for i,w in enumerate(parent)if w>>26==3 and ((w&0x3ffffff)<<2|0x10000000)==g.ENTRY];assert len(jal)==1
        coverage=set();count=0
        for c in cases():
            c=replace(c,source_null=int(entry==0x1507003C));initial=g.fixture(c);g.put(initial,GLOBAL,0 if c.route==1 else g.A)
            expected_initial=dict(initial);prior_effect(expected_initial,c)
            expected,calls,answer=g.reference(expected_initial,replace(c,phase=c.phase-32))
            for i,words in enumerate(programs):
                m=Caller(words,initial,c,entry,parent,i==1)
                if not complete:
                    end=entry+4*n;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                    try:m.run()
                    except WindowBoundary:pass
                    else:raise AssertionError('missing call-window boundary')
                    assert m.r[29]==g.STACK+c.phase-32
                else:m.run();assert m.r[29]==g.STACK+c.phase
                assert len(m.previous_calls)==len(m.target_calls)==1
                assert m.service.calls==calls and g.public(m.memory)==g.public(expected)and m.r[2]==answer
                assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp
                coverage.update(m.visits&set(range(entry,entry+4*n,4)))
            count+=1
        assert len(coverage)==n
        bad=parent[:];bad[jal[0]+1]=0x24050001;c=g.Case(duration=1000,channel=255,context=0,source_null=int(entry==0x1507003C));initial=g.fixture(c);g.put(initial,GLOBAL,g.A)
        try:Caller(programs[0],initial,c,entry,bad,False).run()
        except AssertionError:controls.append(hex(entry))
        else:raise AssertionError(('ineffective caller argument control',entry))
        reports.append(dict(entry=hex(entry),words=n,covered=n,complete_wrapper=complete,cases_per_stream=count,preceding_emitter_modeled=True))
    return dict(callers=reports,effective_argument_controls=controls,streams=len(programs),full_15194794_parent_qualified=False,actual_memcpy_connected=True,c_match_credit=0)
