import json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.experiments.game_resource_motion_151563b8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_resource_motion_151563b8_oracle as guest
from tools.tests import game_resource_motion_151563b8_native as native
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.tests import test_game_attachment_effect_150eee00_match as linking
from tools.pad_generated_object import parse_object

def payload(p):
 t,fs,rs=parse_object(p);f=fs['func_151563B8'];return(t[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']})

def main():
 links=[];negative={}
 with patch.object(linking,'match',SimpleNamespace(FUNCTION='func_151563B8')):
  for j in range(6):
   entry=guest.ENTRY+j*0x10000;s={k:v+j*(0x20000 if k=='func_1516972C'else 0x108000)for k,v in guest.SYMS.items()}
   ws,_=linking.linked(out/'qualified-owner.o',entry,s,'rebase-'+str(j),out)
   for c in(guest.Case(),guest.Case(flags=8,remaining=0x8000,rate=0x7FFF),guest.Case(remaining=0,mutation=1),guest.Case(ticks=0x80000000),guest.Case(ticks=0xFFFFFFFF)):
    initial=guest.fixture(c,s);m=guest.Oracle(ws,initial,c,entry=entry,s=s).run();guest.check(m,initial,c,s)
   assert ws==guest.retail_words(s)
   links.append(dict(entry=hex(entry),cases=5))
  cases=list(guest.native_cases())
  for name,b in native.controls().items():
   obj,diag=compile_owner(root,out,native.header+b,'negative-'+name);assert not diag,diag
   ws,pools=linking.linked(obj,guest.ENTRY,guest.SYMS,'negative-link-'+name,out,True);witness=None
   for c in cases:
    initial=guest.fixture(c);initial.update(pools);m=guest.Oracle(ws,initial,c).run();expected,calls,snaps=guest.reference(initial,c)
    if(guest.public(m.memory),m.calls,m.snapshots)!=(guest.public(expected),calls,snaps):witness=c;break
   assert witness is not None,name
   negative[name]=dict(compiled=True,counterexample=vars(witness),public_semantic_witness=True,literal_words=len(ws));print('effective negative',name,flush=True)
  signed=native.selected.replace('(s16)((u32)state->remaining - (u32)D_800BE9E4)','(s16)(state->remaining - D_800BE9E4)')
  for label,b in(('signed',native.header+signed),('noalias',(native.header+native.selected).replace('__attribute__((__may_alias__))',''))):
   obj,diag=compile_owner(root,out,b,label+'-IDO-control');assert not diag and payload(obj)==payload(out/'qualified-owner.o'),(label,diag)
 report=dict(GNU_links=6,rebased_cases=30,links=links,semantic_controls=negative,signed_and_noalias_IDO_bodies_identical=True,native_only_controls_separate=True)
 (out/'rebases-controls.json').write_text(json.dumps(report,indent=2)+'\n');print('Rebases and controls passed.',flush=True)
if __name__=='__main__':main()
