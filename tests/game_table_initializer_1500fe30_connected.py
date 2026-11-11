"""Private retail bzero integration and bounded null-allocation observation."""
import itertools,json,struct
from tools.experiments import game_table_initializer_1500fe30_match as p
from tools.tests import game_table_initializer_1500fe30_oracle as g
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes()
 target=struct.unpack_from('>91I',rom,p.ROM);original=struct.unpack_from('>39I',rom,0x226f0)
 code=dict(zip(range(g.ZERO,g.ZERO+4*len(original),4),original));visits=set();count=0
 for mutation,seed,phase in itertools.product((0,1),range(4),(0,8)):
  c=g.Case(mutation,seed,phase);m=g.Oracle(target,c,connected=code);m.run();want,calls=g.reference(c,m.initial)
  assert g.public(m.memory)==g.public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls)
  visits.update(m.visits);count+=1
 class NullAllocation(g.Oracle):
  def hook(self,t):
   super().hook(t)
   if t==g.ALLOC:self.r[2]=0
 c=g.Case(0,0);m=NullAllocation(target,c,connected=code)
 try:m.run()
 except AssertionError as e:assert e.args[0]==('unmapped store',0,4),e
 else:raise AssertionError('Expected unmapped first store when bzero receives null')
 assert m.calls==[(g.ALLOC,(100,1,0,0)),(g.ZERO,(0,100))] and g.read(m.memory,g.GLOBAL)==0
 result=dict(cases=count,original_bzero_words_visited=sum(g.ZERO+4*i in visits for i in range(39)),original_bzero_words=39,null_allocation_unmapped_guest_store=True,allocator_random_and_finish_modeled=True,hardware_null_behavior_not_qualified=True,source_installed=False)
 (p.out/'connected-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
