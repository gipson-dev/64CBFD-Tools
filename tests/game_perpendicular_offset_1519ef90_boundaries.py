"""Fired public memory prefixes; unpassed private homes are outside this relation."""
import itertools,json
from tools.tests import game_perpendicular_offset_1519ef90_oracle as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

class Oracle(g.Oracle):
    def __init__(self,*args,**kwargs):self.public_cut=None;self.public_count=0;self.requested=None;super().__init__(*args,**kwargs)
    def boundary(self,kind,address,size):
        if self.own_instruction and not g.STACK+self.c.phase-64<=address<g.STACK+self.c.phase:
            self.requested=(kind,address,size)
            if self.public_cut==self.public_count:raise AccessBoundary
            self.public_count+=1
    def get(self,address,size):
        if getattr(self,'recording',False):self.boundary('R',address,size)
        return super().get(address,size)
    def put(self,address,value,size):
        if getattr(self,'recording',False):self.boundary('W',address,size)
        return super().put(address,value,size)

def visible(q,c):return {a:v for a,v in q.memory.items() if not g.STACK+c.phase-64<=a<g.STACK+c.phase}
def trace(q,c):return [v for v in q.trace if not g.STACK+c.phase-64<=v[1]<g.STACK+c.phase]

def main():
    streams=g.s.programs();streams['guarded']=bound_blob(*payload(g.s.OUT/'guarded.o',g.s.NAME),g.s.symbols());cuts=0
    for near,present,mode,alias,effects in itertools.product((False,True),(0,1),(6,7),(0,3,5),(0,3)):
        c=g.Case(dx=0 if near else g.bits(3.),dz=0 if near else g.bits(4.),present=present,mode=mode,alias=alias,effects=effects)
        m=g.fixture(c);full=Oracle(streams['retail'],m.copy(),c);full.root_words=streams['retail'];full.run()
        for cut in range(full.public_count):
            runs=[]
            for n,ws in streams.items():
                q=Oracle(ws,m.copy(),c);q.root_words=ws;q.public_cut=cut
                try:q.run()
                except AccessBoundary:pass
                else:raise AssertionError(('public memory cut did not fire',n,cut))
                assert q.public_count==cut and q.dispatched_word>>26 in(32,33,35,36,37,40,41,43,49,57)
                runs.append(q)
            assert all((q.requested,trace(q,c),visible(q,c),q.calls,q.fp_ops)==(runs[0].requested,trace(runs[0],c),visible(runs[0],c),runs[0].calls,runs[0].fp_ops) for q in runs[1:]),(c,cut,'prefix')
            cuts+=1
    report=dict(fired_public_memory_prefixes=cuts,streams=3,public_memory_calls_and_prior_FP_ops_equal=True,
                unpassed_private_homes_excluded=True,raw_fault_register_equivalence=False)
    (g.s.OUT/'boundary-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
