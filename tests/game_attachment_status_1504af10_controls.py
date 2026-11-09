"""Semantic mutations, guest-only ordering witnesses, both guarded padders and GNU."""
import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_attachment_status_1504af10_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_attachment_status_1504af10_oracle as guest
from tools.tests import game_attachment_status_1504af10_native as native
from tools.experiments import game_attachment_status_1504af10_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools import pad_generated_object as generated
sys.modules.setdefault('pad_generated_object',generated)
from tools import pad_c_object as generic
def ordering(selected):
 sequence='record->unk4F = (u8)record->unk4F & 0xFF9F;\n            record = &D_800DBEF4[slot];\n            record->unk4F = (u8)record->unk4F | 0x20;'
 x='D_800DBEF4[slot].unk10 = (s32) actor->x_position;';y='D_800DBEF4[slot].unk12 = (s32) (actor->y_position + (s16) actor->unk90);'
 result={'merged-status-stores':selected.replace(sequence,'record->unk4F = ((u8)record->unk4F & 0x9F) | 0x20;'),'cached-table-pointer':selected.replace('    struct131 *record;','    struct131 *record;\n    struct131 *table;').replace('        if (kind == 3) {','        table = D_800DBEF4;\n        if (kind == 3) {').replace('D_800DBEF4[slot]','table[slot]'),'reversed-coordinate-stores':selected.replace(x+'\n            '+y,y+'\n            '+x)}
 assert all(v!=selected for v in result.values());return result
def main():
 owner=(out/'final-owner.c').read_text();selected=body(owner,qualify.FUNCTION);witnesses={};samples=guest.cases()
 for name,part in{**native.mutations(selected),**ordering(selected)}.items():
  obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+name);assert not d,d
  for c in(samples if name not in ordering(selected)else[c for c in samples if c.alias in(2,4)]):
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:m.run();guest.check(m,c)
   except AssertionError as e:assert 'unsupported'not in str(e).lower(),str(e);witnesses[name]=dict(case=repr(c),reason=str(e)[:240],guest_only=name in ordering(selected));break
  else:raise AssertionError('Ineffective IDO control '+name)
 rows=list(csv.DictReader(io.StringIO((out/'proposed-guards.csv').read_text())));indexes=[i for i,r in enumerate(rows)if r['filename']==qualify.OWNER and r['function']==qualify.FUNCTION];assert len(indexes)==30
 temp=out/'stale-guards.csv';single=out/'single-stale-guards.csv';rejections={'generic':0,'generated':0};shapes={'generic':0,'generated':0}
 def manifest(values):
  for p,vs in((temp,values),(single,[v for v in values if v['filename']==qualify.OWNER and v['function']==qualify.FUNCTION])):
   with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(vs)
 def emit(kind):
  if kind=='generated':return generated.emit_padded_assembly(out/'independent-raw.o',out/'retail-layout.s',filename=qualify.OWNER,word_patches_path=single)
  return generic.emit_padded_assembly(out/'qualified-owner.o',root/'conker/retail_layout.us.txt',qualify.OWNER,word_patches_path=temp)
 for key in('expected','expected_relocations'):
  for i in(indexes if key=='expected'else indexes[:1]):
   values=[dict(r)for r in rows];values[i][key]='0x%08X'%(int(values[i][key],0)^1)if key=='expected'else'R_MIPS_HI16:D_80000000';manifest(values)
   for kind in rejections:
    try:emit(kind)
    except ValueError as e:assert 'stale'in str(e).lower()and'expected'in str(e).lower()and qualify.FUNCTION in str(e),str(e);rejections[kind]+=1
    else:raise AssertionError('Stale guard accepted')
 for i in(i for i in indexes if rows[i]['insert_after']):
  for change in('missing','wrong'):
   values=[dict(r)for r in rows]
   if change=='missing':values[i]['insert_after']='';values[i]['insert_after_relocations']=''
   else:values[i]['insert_after']='0x%08X'%(int(values[i]['insert_after'],0)^4)
   manifest(values)
   for kind in rejections:
    obj=qualify.assemble(emit(kind),'bad-insert-'+kind+'-'+str(i)+'-'+change);assert qualify.payload(obj)!=qualify.payload(out/'retail-reference.o');shapes[kind]+=1
 raw,refs=qualify.payload(out/'qualified-owner.o');reject_payload=0
 for offset in range(121):
  bad=bytearray(raw);bad[offset*4]^=1
  try:qualify.checked(bytes(bad),refs)
  except ValueError:reject_payload+=1
  else:raise AssertionError('Changed direct body accepted')
 if not hasattr(qualify,'FROZEN'):qualify.FROZEN=json.loads((out/'freeze-inputs.json').read_text())
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[qualify.ROM:qualify.ROM+492];offsets=(0,qualify.elf_slot_offset(actual,qualify.ENTRY,492),qualify.elf_slot_offset(actual,guest.HELPER,28),qualify.elf_slot_offset(actual,0x15F00000,80),qualify.elf_slot_offset(actual,0x80082B20,4),len(actual)-1)
 for at in offsets:
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truth)
  except AssertionError:pass
  else:raise AssertionError('Image corruption accepted')
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(func_1504AEF4=0x15300000,D_800DBEF4=0x80300000+low,D_800CC2D0=0x80400000+low);entry=0x15340000;dest=out/('rebase-'+hex(low)+'.elf');subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',qualify.FUNCTION,*[a for n,v in s.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/'independent-raw.o')],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,484);ws=list(struct.unpack_from('>121I',data,at));assert ws==guest.words(out/'qualified-owner.o',s);links+=1
  for phase in(0,8):
   for flags in(1,0x3001):
    c=guest.replace(guest.Case(),flags=flags,phase=phase,answer=3,effects=1);m=guest.Oracle(ws,guest.fixture(c,s),c,entry=entry,s=s);m.run();guest.check(m,c,s);executions+=1
 report=dict(effective_IDO_controls=witnesses,stale_guards_rejected=rejections,bad_insertion_shapes_rejected=shapes,corrupt_payloads_rejected=reject_payload,whole_image_corruptions=len(offsets),GNU_links=links,GNU_executions=executions,native_controls=12,additional_guest_ordering_controls=3,compiler_or_interpreter_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=len(witnesses),stale_guards=rejections,bad_insertions=shapes,GNU_links=links,GNU_executions=executions)),flush=True);return report
if __name__=='__main__':main()
