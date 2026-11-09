"""Effective semantic controls and both padder insertion/guard boundaries."""
import csv,io,json,struct,sys,subprocess
from pathlib import Path
from tools.experiments.game_actor_height_result_1504715c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_actor_height_result_1504715c_oracle as guest
from tools.tests import game_actor_height_result_1504715c_native as native
from tools.experiments import game_actor_height_result_1504715c_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools import pad_generated_object as generated
sys.modules.setdefault('pad_generated_object',generated)
from tools import pad_c_object as generic
def main():
 source=(out/'final-owner.c').read_text();selected=body(source,'func_1504715C');witnesses={}
 samples=[guest.Case(),guest.replace(guest.Case(),flags=0),guest.replace(guest.Case(),identity=0),guest.replace(guest.Case(),identity=2),guest.replace(guest.Case(),output_mode=3),guest.replace(guest.Case(),output_mode=2),guest.replace(guest.Case(),effects=7)]
 for name,part in native.mutations(selected).items():
  obj,d=compile_owner(root,out,source.replace(selected,part),'control-'+name);assert not d,d
  for c in samples:
   model=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:model.run();guest.check(model,c)
   except AssertionError as e:
    assert 'unsupported'not in str(e).lower(),str(e);witnesses[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective control: '+name)
 guard=(out/'proposed-guards.csv').read_text();rows=list(csv.DictReader(io.StringIO(guard)));indexes=[i for i,r in enumerate(rows)if r['filename']==qualify.OWNER and r['function']==qualify.FUNCTION];assert len(indexes)==54
 temp=out/'stale-guards.csv';counts={'generated':0,'generic':0};shape={}
 kinds=(('generated',generated.emit_padded_assembly,(out/'qualified-owner.o',root/qualify.ASM),dict(filename=qualify.OWNER)),('generic',generic.emit_padded_assembly,(out/'qualified-owner.o',root/'conker/retail_layout.us.txt',qualify.OWNER),{}))
 def manifest(values):
  with temp.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(values)
 for key in('expected','expected_relocations'):
  for i in(indexes if key=='expected'else indexes[:1]):
   modified=[dict(r)for r in rows];modified[i][key]='0x%08X'%(int(modified[i][key],0)^1)if key=='expected'else'R_MIPS_HI16:D_80000000';manifest(modified)
   for kind,emit,args,kwargs in kinds:
    try:emit(*args,**kwargs,word_patches_path=temp)
    except ValueError as e:assert 'stale'in str(e).lower()and'expected'in str(e).lower()and'func_1504715C'in str(e),str(e);counts[kind]+=1
    else:raise AssertionError('Stale guard accepted: '+kind)
 for i in(i for i in indexes if rows[i]['insert_after']):
  for change in('missing','wrong'):
   modified=[dict(r)for r in rows]
   if change=='missing':modified[i]['insert_after']='';modified[i]['insert_after_relocations']=''
   else:modified[i]['insert_after']='0x%08X'%(int(modified[i]['insert_after'],0)^4)
   manifest(modified)
   for kind,emit,args,kwargs in kinds:
    text=emit(*args,**kwargs,word_patches_path=temp);p=out/('control-insert-'+kind+'-'+str(i)+'-'+change+'.s');p.write_text(text);obj=p.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
    assert qualify.payload(obj)!=qualify.payload(out/'retail-reference.o'),'Bad insertion passed exact-body gate';shape[kind]=shape.get(kind,0)+1
 report=dict(effective_guest_controls=witnesses,stale_guards_rejected=counts,incorrect_insertion_shapes_rejected=shape,raw_word_guards=54,guarded_insertions=2)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_guest_controls=len(witnesses),stale_guards_rejected=counts,insertion_shapes_rejected=shape)),flush=True);return report
if __name__=='__main__':main()
