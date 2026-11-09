"""Effective source mutations, guarded padders, payload/image corruptions and GNU links."""
import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_node_range_walker_15169070_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_node_range_walker_15169070_oracle as guest
from tools.tests import game_node_range_walker_15169070_native as native
from tools.experiments import game_node_range_walker_15169070_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools import pad_generated_object as generated
sys.modules.setdefault('pad_generated_object',generated)
from tools import pad_c_object as generic
def main():
 owner=(out/'final-owner.c').read_text();selected=body(owner,qualify.FUNCTION);witnesses={};samples=guest.cases();diagnostics=qualify.diagnostic_rows((out/'selected-diagnostics.txt').read_text())
 for name,part in native.mutations(selected).items():
  obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+name);assert qualify.diagnostic_rows(d)==diagnostics,d
  for c in samples:
   m=guest.Oracle(guest.words(obj),guest.fixture(c),c,connected=guest.helper_code()if c.real_helpers else None)
   try:m.run();guest.check(m,c)
   except AssertionError as e:
    assert all(k not in str(e).lower()for k in('unsupported','unbounded')),str(e);witnesses[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective IDO control '+name)
 rows=list(csv.DictReader(io.StringIO((out/'proposed-guards.csv').read_text())));indexes=[i for i,r in enumerate(rows)if r['filename']==qualify.OWNER and r['function']==qualify.FUNCTION];assert len(indexes)==45 and not any(rows[i]['insert_after']or rows[i]['omit']=='true'for i in indexes)
 temp=out/'stale-guards.csv';single=out/'single-stale-guards.csv';rejections={'generic':0,'generated':0}
 for key in('expected','expected_relocations'):
  for i in(indexes if key=='expected'else[i for i in indexes if rows[i]['expected_relocations']!='-']):
   values=[dict(r)for r in rows];values[i][key]='0x%08X'%(int(values[i][key],0)^1)if key=='expected'else'R_MIPS_HI16:D_80000000'
   for p,vs in((temp,values),(single,[v for v in values if v['filename']==qualify.OWNER and v['function']==qualify.FUNCTION])):
    with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(vs)
   for kind in rejections:
    try:
     if kind=='generic':generic.emit_padded_assembly(out/'selected.o',root/'conker/retail_layout.us.txt',qualify.OWNER,word_patches_path=temp)
     else:generated.emit_padded_assembly(out/'independent-raw.o',out/'retail-layout.s',filename=qualify.OWNER,word_patches_path=single)
    except ValueError as e:assert 'stale'in str(e).lower()and'expected'in str(e).lower()and qualify.FUNCTION in str(e),str(e);rejections[kind]+=1
    else:raise AssertionError('Stale guard accepted')
 raw,refs=qualify.payload(out/'selected.o');reject_payload=0
 for offset in range(124):
  bad=bytearray(raw);bad[offset*4]^=1
  try:qualify.checked(bytes(bad),refs)
  except ValueError:reject_payload+=1
  else:raise AssertionError('Changed source payload accepted')
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[qualify.ROM:qualify.ROM+496];offsets=(0,qualify.elf_slot_offset(actual,qualify.ENTRY,496),qualify.elf_slot_offset(actual,guest.CLAMP,144),qualify.elf_slot_offset(actual,0x15F00000,80),qualify.elf_slot_offset(actual,0x80082B20,4),len(actual)-1)
 for at in offsets:
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truth)
  except AssertionError:pass
  else:raise AssertionError('Image corruption accepted')
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(guest.SYMS,func_15143D18=0x15300000,func_1516968C=0x15310000,D_8008B4A8=0x80300000+low,D_800DCE50=0x80400000+low,D_800DD190=0x80400340+low,D_800DD198=0x80400348+low);entry=0x15340000;dest=out/('rebase-'+hex(low)+'.elf');subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',qualify.FUNCTION,*[a for n,v in s.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/'independent-raw.o')],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,496);ws=list(struct.unpack_from('>124I',data,at));assert ws==guest.words(out/'selected.o',s);links+=1
  for phase in(0,8):
   for mode in(0,15):
    c=guest.replace(guest.Case(),phase=phase,mode=mode);m=guest.Oracle(ws,guest.fixture(c,s),c,s,entry=entry);m.run();guest.check(m,c,s);executions+=1
 rejected=0
 for d in(-4,4,0x10000):
  try:guest.fixture(guest.Case(),dict(guest.SYMS,D_800DD190=guest.SYMS['D_800DD190']+d))
  except AssertionError:rejected+=1
  else:raise AssertionError('Unqualified row-end binding accepted')
 report=dict(effective_IDO_controls=witnesses,stale_guards_rejected=rejections,corrupt_payloads_rejected=reject_payload,whole_image_corruptions=len(offsets),GNU_links=links,GNU_executions=executions,row_end_binding_preconditions_rejected=rejected,coherent_rebases_only=True,native_controls=12,compiler_interpreter_or_sanitizer_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=len(witnesses),stale_guards=rejections,GNU_links=links,GNU_executions=executions)),flush=True);return report
if __name__=='__main__':main()
