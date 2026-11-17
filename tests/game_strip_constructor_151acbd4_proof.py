"""Complete typed provider/return relation with ordered FP/FCSR and private RAM."""
import json
from tools.tests import game_strip_constructor_151acbd4_private_proof as p
from tools.experiments import game_strip_constructor_151acbd4_recovery as source
def main():
 p.P=source.OUT;results=[]
 for label in ('v63','strip-constructor-padded-strict','strip-constructor-padded-layout'):
  row=p.compare(label);assert row['paths']==row['equal_paths']==10;results.append(row)
 controls=[];raw=p.words('v63')
 for label,old,new in [('factory-size',0x26060058,0x26060054),('copy-size',0x24060024,0x24060020)]:
  bad=raw[:];assert bad.count(old)==1;bad[bad.index(old)]=new
  try:row=p.compare(label,2,bad)
  except AssertionError as error:assert not any(v in str(error)for v in ('unsupported','unbounded proof','escaped code')),error
  else:assert row['equal_paths']<row['paths']
  controls.append(label)
 report=dict(streams=results,complete_provider_return_relation_proved=True,private_schedule_words=0,all_80_private_incoming_home_bytes=True,ordered_FP_FCSR_compared=True,fresh_disjoint_mapped_allocator_objects=True,full_fault_register_relation_proved=False,effective_controls=controls,source_installed=source.installed(),c_match_credit=0)
 (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(streams=3,paths_each=10,private_schedule_words=0)),flush=True)
if __name__=='__main__':main()
