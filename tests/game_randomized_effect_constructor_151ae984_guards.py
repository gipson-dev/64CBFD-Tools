import csv,json,sys
from pathlib import Path
from tools.experiments import game_randomized_effect_constructor_151ae984_match as p
out=p.out;root=p.root
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def main():
 guard=out/'target_151AE984_guards.csv';obj=out/'target_151AE984_raw.o';layout=out/'target_151AE984_layout.csv';asm=out/'original_151AE984_target.s';name='generated_1D92F0'
 with guard.open(newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 assert len(rows)==17;checks=0
 for i in range(len(rows)):
  changed=[dict(r)for r in rows];changed[i]['expected']=hex(int(changed[i]['expected'],0)^1);temp=out/'mutant_151AE984_guards.csv'
  with temp.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(changed)
  for run in (lambda:pad_c_object.emit_padded_assembly(obj,layout,name,word_patches_path=temp),lambda:pad_generated_object.emit_padded_assembly(obj,asm,filename=name,word_patches_path=temp)):
   try:run()
   except ValueError:checks+=1
   else:raise AssertionError(('corruption accepted',i))
 report=dict(rejected_corruptions=checks,guard_rows=17,padders=2,source_installed=False);(out/'guards_151AE984_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
