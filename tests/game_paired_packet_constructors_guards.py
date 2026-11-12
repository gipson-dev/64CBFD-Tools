import csv,json,sys
from pathlib import Path
from tools.experiments import game_paired_packet_constructors_match as p
out=p.out;root=p.root
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def main():
 checks=0
 for name in ('func_1514E00C','func_1514E194'):
  guard=out/(name+'_guards.csv');obj=out/(name+'_raw.o');layout=out/(name+'_layout.csv');asm=out/(name+'_retail_target.s')
  with guard.open(newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
  assert len(rows)==11
  for i in range(len(rows)):
   changed=[dict(r)for r in rows];changed[i]['expected']=hex(int(changed[i]['expected'],0)^1);temp=out/(name+'_mutant.csv')
   with temp.open('w',newline='')as f:
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(changed)
   for run in (lambda:pad_c_object.emit_padded_assembly(obj,layout,'generated_179F30',word_patches_path=temp),lambda:pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_179F30',word_patches_path=temp)):
    try:run()
    except ValueError:checks+=1
    else:raise AssertionError((name,'corruption accepted',i))
 report=dict(targets=2,guard_rows_each=11,rejected_corruptions=checks,padders=2,source_installed=False);(out/'guard_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
