"""Discriminating IDO mutations and fail-closed expected-word/relocation guards."""
import csv,io,json,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_actor_angle_resource_150de458_match import ROOT,BUILD,NEW_SOURCE,HEADERS
root=ROOT;out=root/BUILD
from tools.tests import game_actor_angle_resource_150de458_oracle as guest
from tools.tests import game_actor_angle_resource_150de458_native as native
from tools.experiments import game_position_sound_150f20f0_match as shared
from tools.experiments.game_remaining_donor_candidates import compile_owner
def main():
 results={};cases=list(guest.cases())
 for name,text in native.controls().items():
  obj,diagnostics=compile_owner(root,out,native.header+text,'negative-'+name);assert not diagnostics,diagnostics
  ws=guest.words(obj);witness=None
  for c in cases:
   initial=guest.fixture(c)
   try:
    m=guest.Oracle(ws,initial,c).run();want,calls=guest.reference(initial,c)
    failed=(guest.public(m.memory),m.calls)!=(guest.public(want),calls)
   except(AssertionError,KeyError):failed=True
   if failed:witness=c;break
  assert witness is not None,name;results[name]=dict(compiled=True,counterexample=vars(witness));print('effective',name,flush=True)
 # Touch only one proposed row in a private manifest. Both independent padders
 # must reject stale compiler words and mismatched relocation annotations.
 rows=list(csv.DictReader(io.StringIO((out/'proposed-guards.csv').read_text())));targets=[r for r in rows if r['function']=='func_150DE458'];assert len(targets)==7
 probes=[]
 for kind in('word','relocation'):
  copied=[dict(r)for r in rows];row=next(r for r in copied if r['function']=='func_150DE458'and(kind=='word'or r['expected_relocations']!='-'))
  if kind=='word':row['expected']='0x%08X'%(int(row['expected'],16)^1)
  else:row['expected_relocations']='-'
  p=out/('stale-'+kind+'.csv');stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(copied);p.write_text(stream.getvalue())
  for generated in(True,False):
   with patch.multiple(shared,FUNCTION='func_150DE458',OWNER='generated_10B7D0',SOURCE='conker/src/game/generated_10B7D0.c',OBJECT='conker/build/src/game/generated_10B7D0.c.o',ASM='conker/asm/10B7D0.s',ENTRY=guest.ENTRY,GUARDS=str(p.relative_to(root))):
    try:shared.padded(root,out,out/'qualified-owner.o','stale-'+kind+str(generated),generated)
    except ValueError as error:assert 'patch'in str(error).lower()or 'relocation'in str(error).lower()or 'expected'in str(error).lower(),str(error)
    else:raise AssertionError('Stale guard accepted')
   probes.append(dict(kind=kind,generated_padder=generated,rejected=True))
 report=dict(semantic_controls=results,guard_rejections=probes,history_prefix_exact=(out/'proposed-guards.csv').read_bytes().startswith((out/'frozen/conker/retail_word_patches.us.csv').read_bytes()))
 (out/'controls-contract.json').write_text(json.dumps(report,indent=2)+'\n');print('Controls and stale guards passed.',flush=True)
if __name__=='__main__':main()
