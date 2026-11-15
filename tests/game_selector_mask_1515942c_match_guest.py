"""Three instruction streams, complete access traces and fired memory prefixes."""
import itertools,json,os
from tools.experiments import game_selector_mask_1515942c_match as spec
os.environ['SELECTOR_CANDIDATE']=str(spec.OUT/'qualified.o')
from tools.tests.game_selector_mask_1515942c_common import *
from tools.tests.game_owner_float_payload_oracle import faults
from tools.experiments.game_paired_ground_constructor_match import payload
streams={**programs,'guarded':bound_blob(*payload(spec.OUT/'guarded.o',spec.NAME),spec.symbols())}

def main():
    count=0;visited={name:set() for name in streams}
    def machine(name,m,c):
        q=Oracle(streams[name],m,c).run()
        visited[name].update((pc-entry)//4 for pc in q.visits if entry<=pc<entry+len(streams[name])*4)
        return q
    vals=(-32768,-33,-1,0,1,2,31,32,32767)
    for i in range(1024):
        values=tuple(vals[((i>>(2*j))+(i*(j+1)))%len(vals)] for j in range(5))
        fields=tuple((i*(13+2*j)+j*31)&255 for j in range(5))
        for found,mutate in itertools.product((False,True),(0,1)):
            c=Scenario(values,fields,found,mutate);m=fixture(c);runs=[machine(name,m.copy(),c) for name in streams]
            for q in runs:assert q.r[2]==result(c) and len(q.calls)==1
            assert all((q.trace,q.memory,q.calls)==(runs[0].trace,runs[0].memory,runs[0].calls) for q in runs[1:])
            count+=1
    # Explicit sentinel combinations exercise all ten conditional shift sites.
    for bits in range(32):
        c=Scenario(tuple(-1 if bits>>j&1 else j for j in range(5)),(0,1,2,3,4),True,0);m=fixture(c)
        for name in streams:machine(name,m.copy(),c)
    assert {name:len(v) for name,v in visited.items()}=={'retail':90,'candidate':100,'guarded':90}
    prefixes=0
    for c in (Scenario((-1,)*5,(0,)*5,False),Scenario((-1,)*5,(0,)*5,True),Scenario((-32768,31,32,32767,-33),(255,)*5,True,1)):
        m=fixture(c);whole=Oracle(streams['retail'],m.copy(),c).run()
        for cut in range(whole.all_accesses):
            runs=[]
            for name,ws in streams.items():
                q=Oracle(ws,m.copy(),c);q.cut=cut
                try:q.run()
                except faults.AccessBoundary:pass
                else:raise AssertionError(('memory boundary did not fire',name,cut))
                assert q.all_accesses==cut and q.dispatched_word>>26 in(32,33,35,36,37,40,41,43)
                runs.append(q)
            assert all((q.trace,q.memory,q.calls)==(runs[0].trace,runs[0].memory,runs[0].calls) for q in runs[1:])
            prefixes+=1
    report=dict(cases_per_stream=count+32,streams=3,visited_words={k:len(v) for k,v in visited.items()},
                complete_memory_and_access_traces_equal=True,fired_memory_prefixes=prefixes,full_fault_register_equivalence=False)
    (spec.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
