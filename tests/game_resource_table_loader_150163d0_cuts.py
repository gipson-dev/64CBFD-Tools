import json,struct
from tools.tests import game_resource_table_loader_150163d0_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 lookup={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};programs=[]
 for tag in ('padded_150163D0_generic','padded_150163D0_generated','original_150163D0'):
  data,fs,rs=parse_object(g.out/(tag+'.o'));a,n=fs['func_150163D0']['value'],fs['func_150163D0']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};syms={nm:lookup.get(nm,int(nm[2:],16)if nm.startswith('D_')else 0)for es in refs.values()for _,nm in es};programs.append(bound_blob(data[a:a+n],refs,syms))
 def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 cuts=0
 for c in (g.Case(0,1,3),g.Case(1,1,4),g.Case(5,1,5),g.Case(9,1,6),g.Case(5,0,7),g.Case(5,0x80000000,8)):
  full=g.Oracle(programs[0],c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing cut',c,cut))
    models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]),(c,cut);cuts+=1
 report=dict(access_cut_triples=cuts,hardware_or_native_fault_not_qualified=True,source_installed=False);(g.out/'cuts_150163D0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
