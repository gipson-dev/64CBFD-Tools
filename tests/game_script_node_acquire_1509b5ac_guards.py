"""Reject individually stale instruction and relocation guard preimages."""
import csv,io
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
from tools import pad_c_object as pc

text=(source.OUT/'proposed-guards.csv').read_text();lines=text.splitlines(keepends=True)
rows=list(csv.DictReader(io.StringIO(text)));assert len(lines)==len(rows)+1
bad=source.OUT/'invalid-guards.csv';count=0
for i,row in enumerate(rows):
 if row['function']!=source.NAME:continue
 for field in (3,5):
  fields=lines[i+1].split(',')
  fields[field]='0x%08X'%(int(fields[field],0)^1) if field==3 else 'R_MIPS_LO16:invalid'
  copy=lines[:];copy[i+1]=','.join(fields);bad.write_text(''.join(copy))
  try:pc.emit_padded_assembly(source.OUT/'durable-after.o',source.ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=bad)
  except ValueError:count+=1
  else:raise AssertionError(('stale guard accepted',row['offset'],field))
assert count==12
print(count,'single-guard instruction and relocation corruptions rejected',flush=True)
