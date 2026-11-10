"""Effective compiled semantic counterexamples; execution errors are not witnesses."""
import json
from tools.experiments import game_slot_allocation_1505ed34_match as p
from tools.tests import game_slot_allocation_1505ed34_oracle as g
def main():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=(p.out/'selected-body.c').read_text(encoding='utf-8');needle='func_15060F28(actor, 0);';chunks=source.split(needle);assert len(chunks)==4
 variants={
  'first-scan-bound24':source.replace('index < 25','index < 24',1),
  'detached-scan-bound24':source.replace('index < 25 && (','index < 24 && (',1),
  'recycle-scan-bound24':source.replace('index < 25 && actor->interaction_state != 0x27','index < 24 && actor->interaction_state != 0x27',1),
  'wrong-state39':source.replace('0x27','0x26'),
  'drop-null-priority':source.replace('(actor->interaction_state != 0x27 || actor->unk1D4 != NULL)','actor->interaction_state != 0x27'),
  'wrong-compound-filter':source.replace('0x27 || actor->unk1D4','0x27 && actor->unk1D4'),
  'skip-initializer':source.replace('    func_1505F188(actor);',''),
  'wrong-initializer-slot':source.replace('func_1505F188(actor);','func_1505F188(actor + 1);'),
  'null-return':source.replace('return (u8 *)actor;','return NULL;'),
  'next-pointer-return':source.replace('return (u8 *)actor;','return (u8 *)(actor + 1);'),
  'wrong-occupied-gates':source.replace('actor->interaction_state != 0) {\n        func_15060F28','actor->interaction_state == 0) {\n        func_15060F28'),
 }
 for i,label in enumerate(('skip-detached-cleanup','skip-recycle-cleanup','skip-reserved-cleanup')):
  variants[label]=''.join(chunk+(needle if j<3 and j!=i else '')for j,chunk in enumerate(chunks))
 cs=[g.Case(empty=24),g.Case(clear=24),g.Case(recycle=24),g.Case(),g.Case(empty=0),g.Case(clear=24,recycle=0),g.Case(reserved=0),g.Case(pattern=39,clear=24)]
 report={}
 for label,selected in variants.items():
  obj,diag=p.compile_owner(p.root,p.out,p.proposal(old,selected),'control-'+label);ws=g.words(obj);witness=None;errors=0
  for c in cs:
   m=g.Oracle(ws,g.fixture(c),c)
   try:m.run()
   except (AssertionError,KeyError,ValueError):errors+=1;continue
   expected,calls,result=g.reference(m.initial,c)
   if(m.calls,g.public(m.memory),m.r[2])!=(calls,g.public(expected),result):witness=dict(case=c.__dict__,normal_completion=True);break
  assert witness is not None,(label,'no normally completed semantic witness',errors)
  report[label]=dict(**witness,execution_errors_before_witness=errors)
 result=dict(controls=len(report),effective_compiled_controls=report,execution_errors_counted_as_witnesses=False);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
