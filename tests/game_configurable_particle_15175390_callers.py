"""Execute five original caller windows and compare complete guarded guest prefixes."""
import itertools,json,struct
from tools.experiments import game_configurable_particle_15175390_match as source
from tools.tests import game_configurable_particle_15175390_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
WINDOWS=((0x15183404,0x15183488,0x1b08b4,0x800a7320),(0x151835d8,0x15183660,0x1b0a88,0x800a7330),(0x15183688,0x15183714,0x1b0b38,0x800a7334),(0x15183724,0x151837b0,0x1b0bd4,0x800a7338),(0x151837c0,0x15183844,0x1b0c70,0x800a733c))

class CallerOracle(g.Oracle):
    def __init__(self,window,initial,c,start,connected):
        FactoryOracle.__init__(self,window,initial,c,entry=start,arguments=g.args(c),connected=connected)
        self.rng=self.allocs=0;self.constructor_calls=[]
    def record_call(self,t):
        if t==source.ENTRY:self.constructor_calls.append(tuple(self.arguments(18)))
        else:super().record_call(t)

class GroundOracle(g.Oracle):
    def __init__(self,words,initial,c,connected):
        FactoryOracle.__init__(self,words,initial,c,entry=source.ENTRY,arguments=g.args(c),connected=connected)
        self.rng=self.allocs=0;self.ground_internal=[]
    def record_call(self,t):
        if t in (0x1510f800,0x150a3a70):self.ground_internal.append((t,tuple(self.arguments(1 if t==0x1510f800 else 2))))
        else:super().record_call(t)
    def hook(self,t):
        if t not in (0x1510f800,0x150a3a70):return super().hook(t)
        if t==0x1510f800:assert self.r[4]==0
        else:g.effects(self.memory,self.case,g.GROUND,len(self.calls),self.rng)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=0;self.hi,self.lo=0xa5000010,0xa5000011

def state(m):return m.memory,m.r,m.f,m.calls,m.trace,m.events,m.hi,m.lo,m.current_pc,m.delay_of

def main():
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes()
    retail=list(struct.unpack_from('>370I',rom,source.ROM));raw=bound_blob(*payload(source.OUT/'selected.o',source.NAME));guard=bound_blob(*payload(source.OUT/'guarded.o',source.NAME));assert guard==retail
    count=0;sites=[]
    for index,(start,end,offset,constant) in enumerate(WINDOWS):
        window=list(struct.unpack_from('>%dI'%((end-start)//4),rom,offset))
        assert window[-2]==0x0c000000|((source.ENTRY>>2)&0x3ffffff)
        for n,slot,ground,mutation,phase in itertools.product((0,1,3),(0,3),(0,1,0x80000001),(0,1,2,3),(0,8)):
            flags,kind,types,model,mask,status=((0x30003,10,0,0,1,2),(0x4d,21,3,2,-1,0),(0x4d,21,3,2,-1,2),(0x7d,68,2,8,-1,2),(0x4d,20,0,6,0,2))[index]
            c=g.Case(count=n,slot=slot,outer=63 if index==0 else 128,inner=0 if index==0 else 16,vertical=30 if index==0 else 32,flags=flags,base_type=kind,type_range=types,base_model=model,model_mask=mask,state=status,base=g.bits(-3.25 if count&1 else .8),spread=g.bits(-.25 if index==4 else .5),ground_flags=ground,mutation=mutation,phase=phase,alias=bool(count&1),fail=2,seed=count%7)
            initial=g.fixture(c)
            for off,v in ((0x68,c.x),(0x6c,c.y),(0x70,c.z),(0x74,c.count),(0x80,c.view),(0x84,c.outer),(0x88,c.vertical),(0x8c,c.inner),(0x90,c.ground_flags)):g.put(initial,g.home(c)+off,g.u32(v))
            g.put(initial,constant,c.base)
            if index==4:g.put(initial,0x800a7340,c.spread)
            want,calls,boundary=g.reference(initial,c);assert boundary is None
            for words in (retail,raw,guard):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+1480,4),words));connected[end]=0
                m=CallerOracle(window,initial,c,start,connected);m.r[16]=slot;before_r=m.r[:];before_f=m.f[:]
                m.code=WindowCode(m.code,m);m.code.ends=(end,)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Missing authentic caller return boundary')
                assert m.constructor_calls==[g.args(c)],(index,c,m.constructor_calls)
                assert (g.public(m.memory),m.calls)==(g.public(want),calls),(index,c,m.calls,calls)
                assert all(m.r[i]==before_r[i] for i in (*range(16,24),29,30)) and m.f[20:]==before_f[20:]
            count+=1
        sites.append(dict(start=hex(start),end=hex(end),jal=hex(end-8),words=len(window)))
    prefixes=0
    for c in (g.Case(count=1,flags=0),g.Case(count=3,mutation=3,alias=True,phase=8),g.Case(count=1,write_surface=False,untouched_surface=g.SURFACES-12)):
        initial=g.fixture(c);full=g.Oracle(retail,initial,c);full.run()
        for cut in range(full.all_accesses):
            models=[]
            for words in (retail,guard):
                m=g.Oracle(words,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing guest memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    ground_code=dict(zip(range(g.GROUND,g.GROUND+215*4,4),struct.unpack_from('>215I',rom,0x13cd88)))
    failed=0;ground_visits=set()
    for old,status,mode,phase,alias in itertools.product((0,g.SURFACES-12,g.SURFACES+12),(0,1),(0,1),(0,8),(False,True)):
        c=g.Case(count=1,write_surface=False,untouched_surface=old,state=status,ground_flags=1,flags=0,ground_height=-10000,mutation=mode,phase=phase,alias=alias)
        initial=g.fixture(c);want,calls,boundary=g.reference(initial,c);assert boundary is None
        for words in (retail,guard):
            m=GroundOracle(words,initial,c,ground_code);m.run()
            assert (g.public(m.memory),m.calls)==(g.public(want),calls),(c,m.calls,calls)
            expected=[]
            for t,a in calls:
                if t==g.GROUND:expected.extend(((0x1510f800,(0,)),(0x150a3a70,(a[0],a[2]))))
            assert m.ground_internal==expected and g.read(m.memory,g.home(c)-0x38)==old
            ground_visits.update(set(ground_code)&m.visits)
        failed+=1
    assert len(ground_visits)==19
    report=dict(caller_cases=count,sites=sites,streams=3,arguments=18,saved_registers_preserved=True,memory_prefixes=prefixes,connected_ground_failure_cases=failed,ground_failure_words=len(ground_visits),raw_fault_order_claimed=False,full_parent_or_provider_claimed=False)
    (source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
