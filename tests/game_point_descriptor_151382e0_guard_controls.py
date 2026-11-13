from pathlib import Path
import csv,io,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
text=(out/'durable-private-guards.csv').read_text();lines=text.splitlines(keepends=True);rows=list(csv.DictReader(io.StringIO(text)));assert len(lines)==len(rows)+1
badpath=out/'interface-invalid-guards.csv';checks=0;counts={}
for index,row in enumerate(rows):
 name=row['function']
 if name not in ('func_151382E0','func_15153F18'):continue
 counts[name]=counts.get(name,0)+1;bits=lines[index+1].split(',');bits[3]='0x%08X'%(int(bits[3],0)^1);modified=lines[:];modified[index+1]=','.join(bits);badpath.write_text(''.join(modified))
 attempts=[lambda:pc.emit_padded_assembly(out/'durable-point-after.o',root/'conker/retail_layout.us.txt','game_161520',rodata_symbol='jtbl_800A4350_game',word_patches_path=badpath,function_objects={'func_15138BC0':out/'durable-caller-after.o'})] if name=='func_151382E0' else [lambda:pc.emit_padded_assembly(out/'durable-helper-after.o',root/'conker/retail_layout.us.txt','generated_17CAF0',word_patches_path=badpath),lambda:pg.emit_padded_assembly(out/'durable-helper-after.o',root/'conker/asm/17CAF0.s',filename='generated_17CAF0',word_patches_path=badpath)]
 for attempt in attempts:
  try:attempt()
  except ValueError as exc:
   assert name in str(exc) or 'patch' in str(exc).lower(),str(exc);checks+=1
  else:raise AssertionError((name,row['offset'],'corrupt expected word accepted'))
assert counts=={'func_151382E0':4,'func_15153F18':16}
print('effective guard corruption controls:',checks,counts,'helper checked with both padders')
