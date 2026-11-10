"""Effective IDO mutations, stale guards, insertion integrity and independent GNU links."""
import csv,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_actor_state_1504be2c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_actor_state_1504be2c_oracle as guest
from tools.tests import game_actor_state_1504be2c_native as native
from tools.experiments import game_actor_state_1504be2c_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER

def main():
 owner=(out/'final-owner.c').read_text();selected=body(owner,qualify.FUNCTION);effective={}
 for name,part in native.mutations(selected).items():
  obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+name);assert not d,d
  for c in native.cases():
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:m.run();guest.check(m,c)
   except AssertionError as e:
    assert not any(n in str(e).lower()for n in('unsupported','unmapped','step limit','timeout')),str(e);effective[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective IDO control '+name)
 raw,refs=qualify.payload(out/'selected.o');rejected=0
 for i in range(146):
  bad=bytearray(raw);bad[i*4]^=1
  try:qualify.checked(bytes(bad),refs)
  except ValueError:rejected+=1
  else:raise AssertionError('Corrupt word accepted')
 for i in refs:
  bad=dict(refs);bad[i]=[('R_MIPS_26','wrong_binding')]
  try:qualify.checked(raw,bad)
  except ValueError:rejected+=1
  else:raise AssertionError('Corrupt binding accepted')
 normal,nrefs=qualify.normalize(raw,refs);rows=qualify.guard_rows(raw,refs,normal,nrefs);stale=0;sys.modules.setdefault('pad_generated_object',qualify.pad_generated_object)
 from tools import pad_c_object
 for index in range(len(rows)):
  changed=[dict(r)for r in rows];changed[index]['expected']='0x%08X'%(int(changed[index]['expected'],16)^1);p=out/'stale-guards.csv'
  with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(changed)
  try:pad_c_object.emit_padded_assembly(out/'independent-raw.o',out/'target-layout.csv',qualify.OWNER,word_patches_path=p)
  except ValueError:stale+=1
  else:raise AssertionError('Stale expected guard accepted')
 changed=[dict(r)for r in rows];insertion=next(r for r in changed if r['insert_after']);insertion['insert_after']='0x%08X'%(int(insertion['insert_after'],16)^1);p=out/'corrupt-insertion.csv'
 with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(changed)
 obj=qualify.assemble(pad_c_object.emit_padded_assembly(out/'independent-raw.o',out/'target-layout.csv',qualify.OWNER,word_patches_path=p),'corrupt-insertion');assert qualify.payload(obj)!=(normal,nrefs)
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[qualify.ROM:qualify.ROM+588];qualify.strict_image(before,actual,truth);h=ELF_HEADER.unpack_from(actual);ss=[SECTION_HEADER.unpack_from(actual,h[6]+i*h[11])for i in range(h[12])];offsets=[0,qualify.elf_slot_offset(actual,qualify.ENTRY,588),qualify.elf_slot_offset(actual,qualify.ENTRY+62*4,4),qualify.elf_slot_offset(actual,0x80082B20,4),ss[9][4]+16,ss[10][4]+1,h[5]+24]
 for at in offsets:
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truth)
  except AssertionError:pass
  else:raise AssertionError('Image corruption accepted')
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n.startswith('func_')else 0x80300000+low+i*0x10000)for i,n in enumerate(guest.SYMS)};entry=0x15340000;dest=out/('rebase-'+hex(low)+'.elf')
  subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',qualify.FUNCTION,*[a for n,v in s.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/'independent-generic.o')],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,588);ws=list(struct.unpack_from('>147I',data,at));assert ws==guest.words(out/'qualified-padded/game_77AD0.c.o',s);links+=1
  for phase in(0,8):
   c=guest.replace(guest.Case(),phase=phase,effects=47,first=0);m=guest.Oracle(ws,guest.fixture(c,s),c,entry=entry,s=s);m.run();guest.check(m,c,s);executions+=1
 report=dict(effective_IDO_controls=effective,corrupt_words_and_bindings_rejected=rejected,stale_expected_rows_rejected=stale,insertion_corruption_detected=True,whole_image_corruptions_rejected=len(offsets),independent_GNU_links=links,GNU_rebase_executions=executions,compiler_or_interpreter_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=len(effective),payload_rejections=rejected,stale_guards=stale,GNU_links=links)),flush=True);return report
if __name__=='__main__':main()
