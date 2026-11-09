import json,sys
from pathlib import Path
from tools.experiments.game_resource_maintenance_1510d404_candidates import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_resource_maintenance_1510d404_oracle as guest
from tools.tests import game_resource_maintenance_1510d404_native as native
from tools.experiments.game_remaining_donor_candidates import compile_owner
def main():
 results={};cases=list(guest.cases())
 for label,part in native.controls().items():
  obj,diagnostics=compile_owner(root,out,native.source.replace(native.BODIES['baseline'],part),'control-'+label);assert not diagnostics,diagnostics
  ws=guest.words(obj);witness=None
  for c in cases:
   initial=guest.fixture(c);want,calls,observations,stop=guest.reference(initial,c);m=guest.Oracle(ws,initial,c)
   try:
    m.run();failed=stop or(guest.public(m.memory),m.calls,m.observations)!=(guest.public(want),calls,observations)
   except guest.DiagnosticBoundary:failed=not stop
   except KeyError:failed=True
   except AssertionError as error:
    if 'Unsupported'in str(error):raise
    failed=True
   if failed:witness=c;break
  assert witness is not None,label;results[label]=dict(compiled=True,counterexample=vars(witness));print('effective '+label,flush=True)
 (out/'controls-contract.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':main()
