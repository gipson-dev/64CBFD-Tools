"""Effective IDO semantic controls, closed omissions, stale guards and GNU rebases."""
import csv,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_path_offset_15078544_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_path_offset_15078544_oracle as guest
from tools.tests import game_path_offset_15078544_native as native
from tools.experiments import game_path_offset_15078544_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER

def mutations(p):
 rows=native.mutations(p);cached=p.replace('    struct127 *target;','    struct127 *target;\n    PathNode8 *cached;');needle='((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D1890 + 1]';first=next(s for s in cached.splitlines()if s.strip().startswith(needle));cached=cached.replace(first,'    cached = &'+needle+';\n'+first,1).replace(needle+'.','cached->');rows['cached-path-node']=cached
 lines=p.splitlines();x=next(s for s in lines if s.strip().startswith(needle)and'].x ='in s);y=next(s for s in lines if s.strip().startswith(needle)and'].pad2 ='in s);rows['reversed-X-Y-publication']=p.replace(x+'\n'+y,y+'\n'+x);assert all(v!=p for v in rows.values());return rows

def main():
 owner=(out/'final-owner.c').read_text();selected=body(owner,qualify.FUNCTION);effective={}
 for name,part in mutations(selected).items():
  obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+name);assert sum(diagnostic_rows(d).values())==13,d
  for c in guest.cases():
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:m.run();guest.check(m,c)
   except AssertionError as e:
    assert not any(n in str(e).lower()for n in('unsupported','unmapped','step limit','timeout')),str(e);effective[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective IDO control '+name)
 raw,refs=qualify.payload(out/'selected.o');rejected=0
 for i in range(152):
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
 assert len([r for r in rows if r['omit']=='true'])==2 and not any(r['insert_after']for r in rows)
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[qualify.ROM:qualify.ROM+600];qualify.strict_image(before,actual,truth);h=ELF_HEADER.unpack_from(actual);ss=[SECTION_HEADER.unpack_from(actual,h[6]+i*h[11])for i in range(h[12])];offsets=[0,qualify.elf_slot_offset(actual,qualify.ENTRY,600),qualify.elf_slot_offset(actual,qualify.ENTRY+56*4,4),qualify.elf_slot_offset(actual,0x80082B20,4),ss[9][4]+16,ss[10][4]+1,h[5]+24]
 for at in offsets:
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truth)
  except AssertionError:pass
  else:raise AssertionError('Image corruption accepted')
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={n:(0x15300000+i*0x100 if n in guest.CALL_NAMES else 0x80300000+low+i*0x10000)for i,n in enumerate(guest.SYMS)};entry=0x15340000;dest=out/('rebase-'+hex(low)+'.elf')
  subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',qualify.FUNCTION,*[a for n,v in s.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/'independent-generic.o')],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,600);ws=list(struct.unpack_from('>150I',data,at));assert ws==guest.words(out/'qualified-padded/game_A28B0.c.o',s);links+=1
  for mode in range(4):
   c=guest.replace(guest.Case(),command=mode*64+3,effects=15,phase=(mode&1)*8);m=guest.Oracle(ws,guest.fixture(c,s),c,entry=entry,s=s);m.run();guest.check(m,c,s);executions+=1
 report=dict(effective_IDO_controls=effective,corrupt_words_and_bindings_rejected=rejected,stale_expected_rows_rejected=stale,closed_private_load_omissions=2,checked_NOP_to_argument_copy=True,whole_image_corruptions_rejected=len(offsets),independent_GNU_links=links,GNU_rebase_executions=executions,compiler_or_interpreter_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=len(effective),payload_rejections=rejected,stale_guards=stale,GNU_links=links)),flush=True);return report
if __name__=='__main__':main()
