"""Effective semantic mutations and stale expected-word/relocation rejection."""
import csv,io,json,struct,sys
from pathlib import Path
from tools.experiments.game_positioned_emitter_150e75a0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_positioned_emitter_150e75a0_oracle as guest
from tools.tests import game_positioned_emitter_150e75a0_native as native
from tools.experiments import game_positioned_emitter_150e75a0_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools import pad_generated_object as generated
sys.modules.setdefault('pad_generated_object',generated)
from tools import pad_c_object as generic
def main():
 source=(out/'final-owner.c').read_text();selected=body(source,'func_150E75A0');controls=native.mutations(selected)
 controls['write-unknown-tail']=selected.replace('descriptor.tag = tag[0];','descriptor.tag = tag[0];\n    descriptor.reserved42[0] = 0;')
 controls['write-unknown-padding']=selected.replace('descriptor.tag = tag[0];','descriptor.tag = tag[0];\n    descriptor.pad11 = 0;')
 witnesses={}
 for name,part in controls.items():
  obj,d=compile_owner(root,out,source.replace(selected,part),'control-'+name);assert not d,d
  rejected=False
  for c in(guest.Case(),guest.replace(guest.Case(),value=0,result=0xFEDCBA98)):
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:m.run();guest.check(m,c)
   except AssertionError as error:
    # An unimplemented opcode is a harness limitation, not a semantic witness.
    if 'Unsupported' in str(error)or'unsupported'in str(error):raise
    witnesses[name]=dict(case=repr(c),reason=str(error)[:240]);rejected=True;break
  assert rejected,'Ineffective guest control: '+name
 guard=(out/'proposed-guards.csv').read_text();rows=list(csv.DictReader(io.StringIO(guard)));indexes=[i for i,r in enumerate(rows)if r['filename']==qualify.OWNER and r['function']==qualify.FUNCTION];assert len(indexes)==43
 counts={'generated':0,'generic':0};temp=out/'stale-guards.csv'
 for key in('expected','expected_relocations'):
  for i in(indexes if key=='expected'else indexes[:1]):
   modified=[dict(r)for r in rows]
   if key=='expected':modified[i][key]='0x%08X'%(int(modified[i][key],0)^1)
   else:modified[i][key]='R_MIPS_HI16:D_80088A64'
   with temp.open('w',newline='')as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(modified)
   for kind,emit,args,kwargs in(('generated',generated.emit_padded_assembly,(out/'qualified-owner.o',root/qualify.ASM),dict(filename=qualify.OWNER)),('generic',generic.emit_padded_assembly,(out/'qualified-owner.o',root/'conker/retail_layout.us.txt',qualify.OWNER),{})):
    try:emit(*args,**kwargs,word_patches_path=temp,rodata_symbol='D_800A1350')
    except ValueError as e:assert 'stale'in str(e).lower()and'expected'in str(e).lower()and'func_150E75A0'in str(e),str(e);counts[kind]+=1
    else:raise AssertionError('Stale guard accepted: '+kind+' '+key)
 report=dict(effective_guest_controls=witnesses,stale_guards_rejected=counts,raw_word_guards=43,extra_relocation_rejection=1)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_guest_controls=len(witnesses),stale_guards_rejected=counts)),flush=True);return report
if __name__=='__main__':main()
