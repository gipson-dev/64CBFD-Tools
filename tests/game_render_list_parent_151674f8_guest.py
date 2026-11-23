"""Whole private parent connected to each already qualified complete leaf."""
from pathlib import Path
import hashlib,json,struct,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_indirect_parent as p
g=p.g;u=p.o
class Parent(p.Parent):
 def record_call(self,t):
  if t==p.RANGE:
   a=tuple(map(g.u32,self.arguments(3)));assert a[0]==p.SELECTOR and a[1]!=a[2]and all((q&3)==0 and g.STACK-512<=q<g.STACK+16 for q in a[1:]),('Invalid range output pointers',a)
   self.parent_events.append((t,a));self.range_calls+=1;return
  super().record_call(t)
def state(m):
 events=[(t,(a[0],'first','last')if t==p.RANGE else a)for t,a in m.parent_events]
 return(g.public(m.memory),m.observations,events,m.called_targets,m.r[2])
def main():
 label=sys.argv[1]if len(sys.argv)>1 else'initial';obj=o/label/'candidate.o';raw,refs=g.payload(obj,'func_151674F8')
 symbols={n:v[1]for _,n,v,_ in g.symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 for n in {n for pairs in refs.values()for _,n in pairs}:assert symbols[n]==g.SYMS[n],n
 source=g.bound_blob(raw,refs,symbols);retail=list(struct.unpack('>348I',(r/'conker/conker.us.bin').read_bytes()[0x1949A8:0x194F18]))
 leaves={name:g.bound_blob(*g.payload(u/path,'func_15168118'),symbols)for name,path in dict(raw='selected-v2/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o').items()}
 cases=p.rows();coverage=set();invocations={k:0 for k in leaves}
 for number,c in enumerate(cases):
  memory,nodes=p.fixture(c);truth=Parent(retail,leaves['retail'],memory,c,nodes).run();want=state(truth)
  for name,leaf in leaves.items():
   machine=Parent(source,leaf,memory,c,nodes).run();got=state(machine)
   if got!=want:
    differing=[(hex(a),want[0].get(a),got[0].get(a))for a in want[0].keys()|got[0].keys()if want[0].get(a)!=got[0].get(a)]
    report=dict(case=number,leaf=name,public_byte_differences=differing[:24],observations_equal=got[1]==want[1],parent_events_equal=got[2]==want[2],called_targets_equal=got[3]==want[3],returned=(got[4],want[4]))
    (o/(label+'-guest-failure.json')).write_text(json.dumps(report,indent=2)+'\n');raise AssertionError(report)
   invocations[name]+=len(machine.called_targets);coverage.update(machine.visits)
 report=dict(raw_words=len(source),retail_words=348,cases_per_leaf_stream=len(cases),invocations=invocations,all_public_memory_provider_observations_parent_events_target_arguments_and_returned_cursors_equal=True,unexecuted_source_words=[i for i in range(len(source))if p.PARENT+4*i not in coverage],source_installed=packet.installed(),matching_credit=0,limits='Complete original/private parent and complete qualified leaves. Range helper, stage callbacks and graphics providers are bounded contracts. Range output local addresses are abstracted after alignment/distinct/frame-bound checks; no raw private/access/FCSR/native or gameplay claim.')
 (o/(label+'-guest.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
