"""Full ordered normal-execution relation under the predecessor's explicit ABI contract.

All16 masked initial count pairs are enumerated. Later helper results, public
memory epochs, FCSR and previously passed private packet mutations remain
symbolic. This does not prove complete private-frame equality, arbitrary fault
prefixes, interrupt-visible state, portable undefined inputs or literal matching.
The predecessor instruction decoder is reused unchanged, with exact input seals.
"""
import contextlib,io,itertools,json
from tools.experiments import game_actor_burst_150bbb5c_full as source
from tools.tests import game_actor_burst_150bbb5c_factory_proof as base

def run(raw_path=None,label='full-normal'):
 source.check_inputs();source.state()
 pairs=((0,0),)if raw_path is not None else tuple(itertools.product(range(4),repeat=2))
 rows=[]
 for pair in pairs:
  with contextlib.redirect_stdout(io.StringIO()):
   row=base.run(raw_path,label+'-'+''.join(map(str,pair)),target=None,count_pair=pair)
  rows.append(dict(count_pair=pair,**row))
 passes=all(row['strict_factory_equal']for row in rows)
 report=dict(passes=passes,count_pairs=len(rows),symbolic_paths=sum(row['paths']for row in rows),
  complete_normal_execution_relation=passes,complete_private_frame_equality=False,
  arbitrary_fault_prefix_equality=False,physical_byte_match=False,source_installed=False,c_match_credit=0,rows=rows)
 if raw_path is None:
  assert all(row['paths']==5 and row['covered_words']==dict(raw=591,retail=587)for row in rows)
 (source.OUT/(label+'-report.json')).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items()if k!='rows'}),flush=True)
 return report
