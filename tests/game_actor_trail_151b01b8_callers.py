"""Original caller prefixes and two complete wrapper routines, with opaque next effect."""
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_actor_trail_151b01b8_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

GLOBAL,NEXT=0x800D154C,0x151B09BC
PARENTS=((0x15194794,8,32,False),(0x15195650,18,32,True),(0x1507003C,18,32,True))

class Caller(g.Oracle):
    def __init__(self,words,initial,c,entry,parent,frame,remap):
        code={g.ENTRY+4*i:w for i,w in enumerate(words)}
        if remap:initial=g.exchange(initial,g.STACK+c.phase-frame)
        FactoryOracle.__init__(self,parent,initial,c,entry=entry,s={},arguments=(0 if c.route==1 else g.A,0 if c.source_null else g.source(c),0xBAD00006),connected=code)
        self.service=g.Service(self.memory,c,g.STACK+c.phase-frame)
        self.target_calls=[];self.next_calls=[]
        self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
    def record_call(self,t):
        if t==g.ENTRY:
            args=tuple(self.arguments(2))
            assert args==(0 if self.case.route==1 else g.A,0 if self.case.source_null else g.source(self.case)),('caller ABI',args)
            self.target_calls.append(args)
        elif t==NEXT:
            args=tuple(self.arguments(5));assert args==(0 if self.case.route==1 else g.A,0 if self.case.source_null else g.source(self.case),1000,255,0)
            self.next_calls.append(args)
        else:super().record_call(t)
    def hook(self,t):
        if t!=NEXT:return super().hook(t)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xE5000099

def run(programs):
    rom=(g.recovery.FROZEN/'conker/conker.us.bin').read_bytes();reports=[];negative=[]
    for entry,n,frame,complete in PARENTS:
        parent=list(struct.unpack_from('>'+str(n)+'I',rom,entry-0x14FD2B50))
        assert parent[0]==0x27BD0000|((-frame)&65535),(hex(entry),hex(parent[0]),frame)
        jal=[i for i,w in enumerate(parent)if w>>26==3 and ((w&0x3ffffff)<<2|0x10000000)==g.ENTRY]
        assert len(jal)==1;coverage=set();count=0
        for seed,route,mutation,phase in itertools.product((0,197),range(4),(0,1,2,4,8,16,31),(0,8)):
            c=g.Case(seed=seed,route=route,identity=0x87,kind=4,category=1,mutation=mutation,phase=phase,source_null=int(entry==0x1507003C))
            initial=g.fixture(c);g.put(initial,GLOBAL,0 if c.route==1 else g.A)
            expected,calls=g.reference(initial,replace(c,phase=c.phase-frame))
            for i,words in enumerate(programs):
                m=Caller(words,initial,c,entry,parent,frame,i==1)
                if not complete:
                    end=entry+4*n;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                    try:m.run()
                    except WindowBoundary:pass
                    else:raise AssertionError('missing caller window end')
                    assert m.r[29]==g.STACK+c.phase-frame
                else:
                    m.run();assert len(m.next_calls)==1 and m.r[29]==g.STACK+c.phase
                assert len(m.target_calls)==1 and m.service.calls==calls and g.public(m.memory)==g.public(expected)
                assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp
                coverage.update(m.visits&set(range(entry,entry+4*n,4)))
            count+=1
        assert len(coverage)==n
        bad=parent[:];bad[jal[0]+1]=0x24050001;c=g.Case(kind=4,source_null=int(entry==0x1507003C));initial=g.fixture(c);g.put(initial,GLOBAL,g.A)
        try:Caller(programs[0],initial,c,entry,bad,frame,False).run()
        except AssertionError:negative.append(hex(entry))
        else:raise AssertionError(('ineffective caller argument control',hex(entry)))
        reports.append(dict(entry=hex(entry),words=n,covered=n,complete_wrapper=complete,cases_per_stream=count,next_provider_opaque=complete))
    result=dict(callers=reports,effective_argument_controls=negative,streams=len(programs),full_15194794_parent_qualified=False,c_match_credit=0)
    return result
