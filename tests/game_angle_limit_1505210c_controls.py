"""Effective IDO controls, direct payload checks, GNU rebases and image corruption."""
import json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_angle_limit_1505210c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_angle_limit_1505210c_oracle as guest
from tools.tests import game_angle_limit_1505210c_native as native
from tools.experiments import game_angle_limit_1505210c_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER
def main():
 selected=body((out/'final-owner.c').read_text(),qualify.FUNCTION);owner=(out/'final-owner.c').read_text();effective={}
 for name,part in native.mutations(selected).items():
  obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+name);assert not d,d
  for c in guest.cases():
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:m.run();guest.check(m,c)
   except AssertionError as e:
    assert 'unsupported'not in str(e).lower(),str(e);effective[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective IDO control '+name)
 raw,refs=qualify.payload(out/'qualified-owner.o');rejected=0
 for i in range(85):
  bad=bytearray(raw);bad[i*4]^=1
  try:qualify.checked(bytes(bad),refs)
  except ValueError:rejected+=1
  else:raise AssertionError('Corrupt direct word accepted')
 for i in refs:
  bad=dict(refs);bad[i]=[('R_MIPS_26','wrong_binding')]
  try:qualify.checked(raw,bad)
  except ValueError:rejected+=1
  else:raise AssertionError('Corrupt direct binding accepted')
 if not hasattr(qualify,'FROZEN'):qualify.FROZEN=json.loads((out/'freeze-inputs.json').read_text())
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[qualify.ROM:qualify.ROM+340];qualify.strict_image(before,actual,truth)
 h=ELF_HEADER.unpack_from(actual);ss=[SECTION_HEADER.unpack_from(actual,h[6]+i*h[11])for i in range(h[12])]
 offsets=[0,qualify.elf_slot_offset(actual,qualify.ENTRY,340),qualify.elf_slot_offset(actual,0x150768DC,8),qualify.elf_slot_offset(actual,0x15F00000,80),ss[9][4]+16,ss[10][4]+1,h[5]+24,qualify.elf_slot_offset(actual,0x80082B20,4)]
 for i,at in enumerate(offsets):
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truth)
  except ValueError:pass
  else:raise AssertionError('Image corruption accepted '+str(i))
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  syms={n:(0x15300000+i*0x100 if n.startswith('func_')else 0x80300000+low+i*0x10000)for i,n in enumerate(guest.SYMS)};entry=0x15340000;dest=out/('rebase-'+hex(low)+'.elf')
  subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',qualify.FUNCTION,*[a for n,v in syms.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/'independent-raw.o')],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,340);ws=list(struct.unpack_from('>85I',data,at));assert ws==guest.words(out/'qualified-owner.o',syms);links+=1
  for phase in(0,8):
   c=guest.replace(guest.Case(),phase=phase,effects=7);m=guest.Oracle(ws,guest.fixture(c,syms),c,entry=entry,s=syms);m.run();guest.check(m,c,syms);executions+=1
 report=dict(effective_IDO_controls=effective,corrupt_words_and_bindings_rejected=rejected,whole_image_corruptions_rejected=len(offsets),independent_GNU_links=links,GNU_rebase_executions=executions,new_guards=0,compiler_or_interpreter_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=len(effective),direct_payload_rejections=rejected,image_corruptions=len(offsets),GNU_links=links,GNU_executions=executions)),flush=True);return report
if __name__=='__main__':main()
