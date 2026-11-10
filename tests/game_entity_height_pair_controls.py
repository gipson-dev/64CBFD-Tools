"""Effective per-function IDO mutations, stale guards, corrupt payloads/images, independent GNU rebases."""
import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_entity_height_pair_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_entity_height_pair_oracle as guest
from tools.tests import game_entity_height_pair_native as native
from tools.experiments import game_entity_height_pair_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools import pad_generated_object as generated
sys.modules.setdefault('pad_generated_object',generated)
from tools import pad_c_object as generic
def main():
 owner=(out/'final-owner.c').read_text();witnesses={}
 for kind,function in enumerate(qualify.FUNCTIONS):
  selected=body(owner,function);found={};samples=[c for c in guest.cases(kind)if c.home_selected==-2 and not c.home_input and c.home_threshold<0]
  for name,part in native.mutations(selected).items():
   obj,d=compile_owner(root,out,owner.replace(selected,part),'control-'+str(kind)+'-'+name);assert not d,d
   for c in samples:
    if c.alias:continue
    m=guest.Oracle(guest.words(obj,kind),guest.fixture(c),c);m.run();want,calls,obs,result=guest.reference(m.initial,c)
    if(guest.public(m.memory),m.calls,m.observations,m.r[2]&0xFFFFFFFF)!=(guest.public(want),calls,obs,result):found[name]=dict(case=repr(c),reason='Independent memory, call observation or return mismatch');break
   else:raise AssertionError('Ineffective IDO control '+function+'/'+name)
  witnesses[function]=found
 rows=list(csv.DictReader(io.StringIO((out/'proposed-guards.csv').read_text())));indexes=[i for i,r in enumerate(rows)if r['filename']==qualify.OWNER and r['function']in qualify.FUNCTIONS];assert len(indexes)==106 and not any(rows[i]['insert_after']or rows[i]['omit']=='true'for i in indexes);temp=out/'stale-guards.csv';single=out/'single-stale-guards.csv';rejections={'generic':0,'generated':0}
 for key in('expected','expected_relocations'):
  for i in(indexes if key=='expected'else[i for i in indexes if rows[i]['expected_relocations']!='-']):
   function=rows[i]['function'];values=[dict(r)for r in rows];values[i][key]='0x%08X'%(int(values[i][key],0)^1)if key=='expected'else'R_MIPS_HI16:D_80000000'
   for p,vs in((temp,values),(single,[v for v in values if v['filename']==qualify.OWNER and v['function']==function])):
    with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(vs)
   for label in rejections:
    try:
     if label=='generic':generic.emit_padded_assembly(out/'selected.o',root/'conker/retail_layout.us.txt',qualify.OWNER,word_patches_path=temp)
     else:generated.emit_padded_assembly(out/(function+'-independent-raw.o'),out/(function+'-layout.s'),filename=qualify.OWNER,word_patches_path=single)
    except ValueError as e:assert 'stale'in str(e).lower()and'expected'in str(e).lower()and function in str(e),str(e);rejections[label]+=1
    else:raise AssertionError('Stale guard accepted')
 reject_payload=0
 for function in qualify.FUNCTIONS:
  raw,refs=qualify.payload(out/'selected.o',function)
  for offset in range(145):
   bad=bytearray(raw);bad[offset*4]^=1
   try:qualify.checked(bytes(bad),refs,function=function)
   except ValueError:reject_payload+=1
   else:raise AssertionError('Changed payload accepted')
 before=(out/'frozen'/qualify.ELF).read_bytes();actual=(out/'qualified-image.elf').read_bytes();rom=(root/'conker/conker.us.bin').read_bytes();truths=[rom[r:r+580]for r in qualify.ROMS];offsets=(0,*[qualify.elf_slot_offset(actual,e,580)for e in qualify.ENTRIES],qualify.elf_slot_offset(actual,guest.CONTEXT,32),qualify.elf_slot_offset(actual,0x15F00000,80),qualify.elf_slot_offset(actual,0x80082B20,4),len(actual)-1)
 for at in offsets:
  bad=bytearray(actual);bad[at]^=1
  try:qualify.strict_image(before,bytes(bad),truths)
  except AssertionError:pass
  else:raise AssertionError('Image corruption accepted')
 links=executions=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={k:(v if k.startswith('func_')else 0x80300000+low+(v&0xFFFFF))for k,v in guest.SYMS.items()};s.update(func_150A44F0=0x15300000,func_150A43E0=0x15310000)
  for kind,function in enumerate(qualify.FUNCTIONS):
   entry=0x15340000;dest=out/('rebase-'+function+'-'+hex(low)+'.elf');subprocess.run(['mips-linux-gnu-ld','-EB','-Ttext',hex(entry),'-e',function,*[a for n,v in s.items()for a in('--defsym',n+'='+hex(v))],'-o',str(dest),str(out/(function+'-independent-raw.o'))],capture_output=True,check=True);data=dest.read_bytes();at=qualify.elf_slot_offset(data,entry,580);ws=list(struct.unpack_from('>145I',data,at));assert ws==guest.words(out/'selected.o',kind,s);links+=1
   for phase in(0,8):
    for mutation in(0,255):
     c=guest.replace(guest.Case(),kind=kind,phase=phase,mutation=mutation);m=guest.Oracle(ws,guest.fixture(c,s),c,s,entry=entry);m.run();guest.check(m,c,s);executions+=1
 report=dict(effective_IDO_controls=witnesses,stale_guards_rejected=rejections,corrupt_payloads_rejected=reject_payload,whole_image_corruptions=len(offsets),GNU_links=links,GNU_executions=executions,native_controls=24,compiler_interpreter_or_sanitizer_errors_counted=False);(out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_IDO_controls=sum(map(len,witnesses.values())),stale_guards=rejections,GNU_links=links,GNU_executions=executions)),flush=True);return report
if __name__=='__main__':main()
