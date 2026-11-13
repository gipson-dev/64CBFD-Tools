from pathlib import Path
import csv,io,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT;text=(out/'proposed-guards.csv').read_text();lines=text.splitlines(keepends=True);rows=list(csv.DictReader(io.StringIO(text)));assert len(lines)==len(rows)+1
bad=out/'invalid-guards.csv';count=0
for i,row in enumerate(rows):
 if row['function']!='func_1517ABB0':continue
 for field in (3,5):
  fields=lines[i+1].split(',');fields[field]='0x%08X'%(int(fields[field],0)^1) if field==3 else 'R_MIPS_LO16:invalid';copy=lines[:];copy[i+1]=','.join(fields);bad.write_text(''.join(copy))
  attempts=(lambda:pg.emit_padded_assembly(out/'variant-split.o',root/'conker/asm/1A8060.s',filename='generated_1A8060',word_patches_path=bad),lambda:pc.emit_padded_assembly(out/'variant-split.o',root/'conker/retail_layout.us.txt','generated_1A8060',word_patches_path=bad))
  for attempt in attempts:
   try:attempt()
   except ValueError:count+=1
   else:raise AssertionError(('stale guard accepted',row['offset'],field))
assert count==64
print(count,'single-guard instruction and relocation corruptions rejected across both padders',flush=True)
