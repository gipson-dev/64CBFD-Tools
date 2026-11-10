"""Discriminating compiler controls, fail-closed guards and independent GNU links."""
import csv,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_water_stun_150585f0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_water_stun_150585f0_oracle as guest
from tools.tests import game_water_stun_150585f0_native as native
from tools.experiments import game_water_stun_150585f0_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER
def mutations(p):
 rows=native.mutations(p);rows['stale-resource']=p.replace('    u16 recovery_heading;','    u8 resource = D_800C3E78;\n    u16 recovery_heading;').replace('func_1505E874(D_800C3E78,','func_1505E874(resource,');rows['stale-carried-byte']=p.replace('    u16 recovery_heading;','    u8 carried = arg0->unk238;\n    u16 recovery_heading;').replace('unk23A = arg0->unk238','unk23A = carried');return rows
def main():
 owner=(out/'final-owner.c').read_text();selected=body(owner,qualify.FUNCTION);effective={}
 for name,part in mutations(selected).items():
  obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+name);assert sum(diagnostic_rows(d).values())==8,d
  for c in guest.cases():
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:m.run();guest.check(m,c)
   except AssertionError as e:
    assert not any(n in str(e).lower()for n in('unsupported','unmapped','step limit','timeout'))and str(e).startswith(("('ABI',","('public',","('snapshots',","('count',")),str(e);effective[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective IDO control '+name)
 raw,refs=qualify.payload(out/'selected.o');rejected=0
 for i in range(171):
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
  try:pad_c_object.emit_padded_assembly(out/'independent-raw.o',out/'target-layout.csv',qualify.OWNER,word_patches_path=p,rodata_symbol=qualify.RODATA)
  except ValueError:stale+=1
  else:raise AssertionError('Stale expected guard accepted')
 assert len([r for r in rows if r['omit']=='true'])==1 and not any(r['insert_after']for r in rows)and len(rows)==11
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[qualify.ROM:qualify.ROM+680];qualify.strict_image(before,actual,truth);h=ELF_HEADER.unpack_from(actual);ss=[SECTION_HEADER.unpack_from(actual,h[6]+i*h[11])for i in range(h[12])];positions=[0,qualify.elf_slot_offset(actual,qualify.ENTRY,680),qualify.elf_slot_offset(actual,qualify.ENTRY+137*4,4),qualify.elf_slot_offset(actual,0x80099484,4),ss[9][4]+16,ss[10][4]+1,h[5]+24]
 for at in positions:
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truth)
  except AssertionError:pass
  else:raise AssertionError('Image corruption accepted')
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n in guest.CALL_NAMES else 0x80300000+low+i*0x10000)for i,n in enumerate(guest.SYMS)};entry=0x15340000;dest=out/('rebase-'+hex(low)+'.elf')
  subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',qualify.FUNCTION,*[a for n,v in s.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/'independent-generic.o')],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,616);ws=list(struct.unpack_from('>170I',data,at));assert ws==guest.words(out/'qualified-padded/game_83300.c.o',s);links+=1
  for mode in range(3):
   c=guest.replace(guest.Case(),stun=(1,2,255)[mode],timer=0,effects=15,phase=(mode&1)*8);m=guest.Oracle(ws,guest.fixture(c,s),c,entry=entry,s=s);m.run();guest.check(m,c,s);executions+=1
 report=dict(effective_IDO_controls=effective,corrupt_words_and_bindings_rejected=rejected,stale_expected_rows_rejected=stale,constant_schedule_qualified=True,whole_image_corruptions_rejected=len(positions),independent_GNU_links=links,GNU_rebase_executions=executions,compiler_or_interpreter_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=len(effective),payload_rejections=rejected,stale_guards=stale,GNU_links=links)),flush=True);return report
if __name__=='__main__':main()
