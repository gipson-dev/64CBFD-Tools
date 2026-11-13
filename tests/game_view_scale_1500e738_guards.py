from pathlib import Path
import csv,io,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;text=(out/'proposed-guards.csv').read_text();lines=text.splitlines(keepends=True);rows=list(csv.DictReader(io.StringIO(text)));bad=out/'invalid-guards.csv';count=0
for i,row in enumerate(rows):
 if row['function']!='func_1500E738':continue
 for field in (3,5):
  fields=lines[i+1].split(',');fields[field]='0x%08X'%(int(fields[field],0)^1) if field==3 else 'R_MIPS_LO16:invalid';copy=lines[:];copy[i+1]=','.join(fields);bad.write_text(''.join(copy))
  try:pc.emit_padded_assembly(out/'variant-case1_default.o',root/'conker/retail_layout.us.txt','game_3BA70',word_patches_path=bad,function_objects={'func_1500E5C0':out/'reset.o'})
  except ValueError:count+=1
  else:raise AssertionError(('stale guard accepted',row['offset'],field))
assert count==4
print(count,'single-guard instruction and relocation corruptions rejected',flush=True)
