from pathlib import Path
import csv,io,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
text=(out/'durable-guards.csv').read_text();lines=text.splitlines(keepends=True);rows=list(csv.DictReader(io.StringIO(text)));assert len(lines)==len(rows)+1;bad=out/'abi-invalid-guards.csv';checked=0
for i,row in enumerate(rows):
 if row['function']!='func_15156028':continue
 fields=lines[i+1].split(',');fields[3]='0x%08X'%(int(fields[3],0)^1);copy=lines[:];copy[i+1]=','.join(fields);bad.write_text(''.join(copy))
 for attempt in (lambda:pg.emit_padded_assembly(out/'durable-after.o',root/'conker/asm/182C30.s',filename='generated_182C30',word_patches_path=bad),lambda:pc.emit_padded_assembly(out/'durable-after.o',root/'conker/retail_layout.us.txt','generated_182C30',word_patches_path=bad)):
  try:attempt()
  except ValueError as exc:assert 'patch' in str(exc).lower() or '15156028' in str(exc);checked+=1
  else:raise AssertionError(('stale guard accepted',row['offset']))
assert checked==102;print(checked,'single-guard corruptions rejected across both padders')
