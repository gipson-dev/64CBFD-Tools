"""Semantic mutation witnesses, stale guard rejection and exact NOP extents."""
import csv,io,json,struct,sys,subprocess
from pathlib import Path
from tools.experiments.game_vertex_quad_1513e13c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_vertex_quad_1513e13c_oracle as guest
from tools.tests import game_vertex_quad_1513e13c_native as native
from tools.experiments import game_vertex_quad_1513e13c_match as qualify
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools import pad_generated_object as generated
sys.modules.setdefault('pad_generated_object',generated)
from tools import pad_c_object as generic

def main():
 source=(out/'final-owner.c').read_text();selected=body(source,qualify.FUNCTION);witnesses={};samples=guest.cases();_,baseline=compile_owner(root,out,source,'control-baseline');expected=diagnostic_rows(baseline);assert sum(expected.values())==43
 for name,part in native.mutations(selected).items():
  obj,d=compile_owner(root,out,source.replace(selected,part),'control-'+name);assert diagnostic_rows(d)==expected,d
  for c in samples:
   model=guest.Oracle(guest.words(obj),guest.fixture(c),c)
   try:model.run();guest.check(model,c)
   except AssertionError as e:
    assert 'unsupported'not in str(e).lower(),str(e);witnesses[name]=dict(case=repr(c),reason=str(e)[:240]);break
  else:raise AssertionError('Ineffective compiled control: '+name)
 guard=(out/'proposed-guards.csv').read_text();rows=list(csv.DictReader(io.StringIO(guard)));indexes=[i for i,r in enumerate(rows)if r['filename']==qualify.OWNER and r['function']==qualify.FUNCTION];assert len(indexes)==55
 temp=out/'stale-guards.csv';singletemp=out/'single-stale-guards.csv';counts={'generated':0,'generic':0};shape={}
 def manifest(values):
  for p,vs in((temp,values),(singletemp,[v for v in values if v['filename']==qualify.OWNER and v['function']==qualify.FUNCTION])):
   with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(vs)
 def emit(kind):
  if kind=='generated':return generated.emit_padded_assembly(out/'independent-padded-raw.o',root/qualify.ASM,filename=qualify.OWNER,word_patches_path=singletemp)
  return generic.emit_padded_assembly(out/'qualified-owner.o',root/'conker/retail_layout.us.txt',qualify.OWNER,word_patches_path=temp,rodata_symbol='jtbl_800A5188_game')
 for key in('expected','expected_relocations'):
  for i in(indexes if key=='expected'else indexes[:1]):
   modified=[dict(r)for r in rows];modified[i][key]='0x%08X'%(int(modified[i][key],0)^1)if key=='expected'else'R_MIPS_HI16:D_80000000';manifest(modified)
   for kind in counts:
    try:emit(kind)
    except ValueError as e:assert 'stale'in str(e).lower()and'expected'in str(e).lower()and qualify.FUNCTION in str(e),str(e);counts[kind]+=1
    else:raise AssertionError('Stale guard accepted: '+kind)
 for i in(i for i in indexes if rows[i]['insert_after']):
  for change in('missing','wrong'):
   modified=[dict(r)for r in rows]
   if change=='missing':modified[i]['insert_after']='';modified[i]['insert_after_relocations']=''
   else:modified[i]['insert_after']='0x00000004'
   manifest(modified)
   for kind in counts:
    obj=qualify.assemble(emit(kind),'control-insert-'+kind+'-'+str(i)+'-'+change)
    assert qualify.payload(obj)!=qualify.payload(out/'retail-reference.o'),'Bad insertion passed exact-body gate';shape[kind]=shape.get(kind,0)+1
 report=dict(effective_guest_controls=witnesses,stale_guards_rejected=counts,incorrect_insertion_shapes_rejected=shape,raw_word_guards=55,guarded_insertions=2,compiler_or_interpreter_errors_counted=False)
 (out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(effective_guest_controls=len(witnesses),stale_guards_rejected=counts,insertion_shapes_rejected=shape)),flush=True);return report
if __name__=='__main__':main()
