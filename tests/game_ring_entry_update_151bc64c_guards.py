import csv,json,sys
from pathlib import Path
from tools.experiments import game_ring_entry_update_151bc64c_match as p
out=p.out;root=p.root
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def main():
 guard=out/'target_151BC64C_guards.csv';obj=out/'target_151BC64C_raw.o';layout=out/'target_151BC64C_layout.csv';asm=out/'original_151BC64C_target.s';name='generated_1E73B0'
 with guard.open(newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 assert len(rows)==29;checks=0
 for i in range(len(rows)):
  changed=[dict(r)for r in rows];changed[i]['expected']=hex(int(changed[i]['expected'],0)^1);temp=out/'mutant_151BC64C_guards.csv'
  with temp.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(changed)
  for run in (lambda:pad_c_object.emit_padded_assembly(obj,layout,name,word_patches_path=temp),lambda:pad_generated_object.emit_padded_assembly(obj,asm,filename=name,word_patches_path=temp)):
   try:run()
   except ValueError:checks+=1
   else:raise AssertionError(('corruption accepted',i))
 report=dict(rejected_corruptions=checks,guard_rows=29,padders=2,source_installed=False);(out/'guards_151BC64C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
