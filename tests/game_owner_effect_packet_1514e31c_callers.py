"""Complete original dispatcher with the callback in all three selected routes.

Selector/classifier providers are controlled interface fixtures; only slot3
and the complete parent body are asserted against retail. No gameplay or
unfinished grandparent acceptance is claimed.
"""
from pathlib import Path
from tools.experiments import game_owner_effect_packet_1514e31c_packet as target_packet
from dataclasses import replace
from unittest.mock import patch
from functools import lru_cache
import hashlib,itertools,json,struct,sys
from tools.tests import game_owner_effect_packet_1514e31c_guest as leaf
from tools.tests import game_owner_action_dispatch_1514d15c_guest as g
from tools.tests.game_owner_action_dispatch_1514d15c_classifier_abi import at
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
R=target_packet.ROOT;O=target_packet.OUT;B=O/'baseline';PARENT=0x1514d15c
leaf.helper_code=lru_cache(None)(leaf.helper_code)
def initial(c,pc):
 m=leaf.fixture(pc);m.update(g.fixture(c));m[g.owner(c)+0x3b]=pc.identity
 for a,k in zip(leaf.GLOBALS,(0,7)):g.put(m,a,leaf.PATTERNS[(pc.seed+k)%14])
 g.put(m,g.TABLE+4*3,leaf.ENTRY)
 return m
class Connected(g.Machine):
 def __init__(self,parent,child,c,pc,memory,deep,poison):
  code=dict(zip(range(leaf.ENTRY,leaf.ENTRY+492,4),child))
  if deep:code.update(leaf.helper_code())
  super().__init__(parent,c,memory,connected=code)
  self.case=pc;self.deep=deep;self.home=STACK+c.phase-72;self.snaps=[];self.poison=poison;self.entries=[]
 def record_call(self,t):
  if t==leaf.ENTRY:
   a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a));self.entries.append(a);self.callback_ordinal+=1
  elif t in (leaf.ALLOC,leaf.ATTACH,leaf.FINAL,leaf.FACTORY,leaf.COPY):leaf.Oracle.record_call(self,t)
  else:super().record_call(t)
 def hook(self,t):
  if t in (leaf.ALLOC,leaf.ATTACH,leaf.FINAL,leaf.FACTORY):
   leaf.Oracle.hook(self,t)
   if t==leaf.FINAL:self.r[2]=self.poison
  else:super().hook(t)
STACK=leaf.STACK
def callback_reference(m,pc,home,deep):
 # The actual callback prologue saves its new owner argument each invocation.
 g.put(m,home,leaf.OWNER)
 return leaf.callback_reference(m,pc,home,deep)

def expected(memory,c,pc,deep,poison):
 old_effect=g.effect;groups=[];snaps=[]
 def service(m,case,t,args,*rest):
  if t!=leaf.ENTRY:return old_effect(m,case,t,args,*rest)
  assert args==(leaf.OWNER,)
  calls,observed=callback_reference(m,pc,STACK+c.phase-72,deep);groups.append(calls);snaps.extend(observed);return poison
 with patch.object(g,'effect',service):public,calls,value=g.reference(memory,c)
 expanded=[];it=iter(groups)
 for t,a in calls:
  expanded.append((t,a))
  if t==leaf.ENTRY:expanded.extend(next(it))
 assert next(it,None)is None
 return public,expanded,value,snaps
def main():
 target_packet.prepare()
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(B/'conker/build/conker.us.elf').read_bytes();body=at(elf,PARENT,436);assert body==rom[0x17a60c:0x17a7c0]
 table=at(elf,g.TABLE,58*4);assert table==rom[0x22f530:0x22f618] and struct.unpack_from('>I',table,12)[0]==leaf.ENTRY
 parents=[bound_blob(*payload(O/p,'func_1514D15C'),g.symbols())for p in ['before-owner.o','qualified-owner/selected-generic.o']];assert len(parents[0])==109 and parents[0]==parents[1]
 children=[leaf.programs()[i][1]for i in (0,2)]
 rows=[]
 for flags,selectors,outcome,mut,home,poison in itertools.product((0,2,3,4,7,255),((0,0,0),(3,0,0),(0,3,0),(0,0,3),(3,3,3)),range(2),range(2),range(4),(0,0xffffffff,0x76543210)):
  c=g.Case(flags=flags,selectors=selectors,effects=outcome,enable=outcome,phase=8*mut,seed=outcome)
  pc=leaf.Case(identity=(0,255)[outcome],success=outcome,mutation=3*mut,home_mutation=home,seed=(0,12)[outcome],phase=c.phase);rows.append((c,pc,poison))
 for index,gate,enabled in itertools.product((-2,0,3),(0,1),(0,1)):
  c=g.Case(index=index,gate=gate,enable=enabled,flags=0,effects=2);rows.append((c,leaf.Case(),0))
 for flags in (3,7):
  c=g.Case(flags=flags,selectors=(0,0,0),absent=1,effects=0);rows.append((c,leaf.Case(),0))
 parent_seen=set();child_seen=set();runs=0;target_calls=0
 for idx,(c,pc,poison) in enumerate(rows):
  memory=initial(c,pc)
  for deep in (False,True):
   want=expected(memory,c,pc,deep,poison);models=[]
   for parent,child in itertools.product(parents,children):
    m=Connected(parent,child,c,pc,memory,deep,poison);m.run()
    assert(g.public(m.memory,c),m.calls,m.r[2],m.snaps)==want,(idx,deep,c,pc,poison,'reference')
    assert all(m.r[i]==m.before[i]for i in (*range(16,24),28,29,30,31)) and m.f[20:]==m.before_f[20:]
    assert all(a==(leaf.OWNER,)for a in m.entries)
    models.append(m);runs+=1;target_calls+=len(m.entries);parent_seen.update(m.visits);child_seen.update(m.visits)
   assert all((g.state(m),m.snaps)==(g.state(models[0]),models[0].snaps)for m in models[1:])
  if idx%256==0:print(json.dumps(dict(caller_cases=idx+1,total=len(rows))),flush=True)
 controls=[];c=g.Case(flags=7,selectors=(3,3,3));pc=leaf.Case(success=1,mutation=3,home_mutation=3);memory=initial(c,pc);want=expected(memory,c,pc,True,0xffffffff)
 for name,alter in [('wrong-callback-table-entry',lambda m:g.put(m,g.TABLE+12,g.CB+3*32)),('missing-selected-route',lambda m:m.__setitem__(g.THIRD+1,0))]:
  bad=dict(memory);alter(bad);m=Connected(parents[0],children[0],c,pc,bad,True,0xffffffff);m.run();assert(g.public(m.memory,c),m.calls,m.r[2],m.snaps)!=want;controls.append(name)
 q=dict(original_parent_words_pinned=109,original_parent_words_executed=sum(PARENT+4*i in parent_seen for i in range(109)),target_words_executed=sum(leaf.ENTRY+4*i in child_seen for i in range(123)),callback_table_entries_pinned=58,actual_callback_slot=3,cases_per_matrix=len(rows),parent_streams=2,child_streams=2,helper_modes=2,connected_runs=runs,target_callback_entries=target_calls,independent_dispatch_and_packet_reference_equal=True,all_three_selected_routes=True,three_child_return_poisons_ignored=True,complete_normalized_private_states_equal=True,raw_literal_caller_fault_parity_claimed=False,classifier_and_selector_routes='controlled interface fixtures; actual route reachability not claimed',unfinished_grandparent_not_executed_or_credited=True,effective_controls=controls,parent_sha256=hashlib.sha256(body).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),source_installed=target_packet.installed(),matching_credit=0)
 assert q['original_parent_words_executed']==109 and q['target_words_executed']==123,(q['original_parent_words_executed'],q['target_words_executed'],[hex(i*4)for i in range(109)if PARENT+4*i not in parent_seen])
 (O/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
