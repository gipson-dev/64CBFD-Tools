"""Exercise guard families through both complete-owner production padders."""
import csv,io,json
from tools.experiments import game_actor_bound_burst_150b7b40_match as source

def controls():
 rows=source.PIN['guard_rows'];selected=set();phase_examples=[]
 def target(row):
  index=int(row['offset'],0)//4;return index+(index>21)
 for phase in source.PIN['normalization']['permutations']:
  choices=[i for i,row in enumerate(rows)if phase['start']<=target(row)<phase['end']]
  if choices:selected.add(choices[0]);phase_examples.append(choices[0])
 inserted=[i for i,row in enumerate(rows)if row['insert_after']];assert len(inserted)==1;selected.update(inserted)
 for j in(68,78,183,209):
  selected.add(next(i for i,row in enumerate(rows)if target(row)==j))
 relocated={}
 for i,row in enumerate(rows):
  for field in('expected_relocations','replacement_relocations'):
   if row[field]!='-':
    for item in row[field].split(';'):relocated.setdefault(item.split(':')[0],i)
 assert set(relocated)=={'R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'};selected.update(relocated.values())
 before=(source.FROZEN/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));count=0
 def rejected(changed,label):
  nonlocal count
  stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writerows(changed)
  path=source.OUT/'invalid-guards.csv';path.write_bytes(before+stream.getvalue().encode())
  for module,layout in((source.pg,source.FROZEN/'conker/asm/E4070.s'),(source.pc,source.FROZEN/'conker/retail_layout.us.txt')):
   try:
    text=module.emit_padded_assembly(source.OUT/'owner.o',layout,filename='generated_E4070',word_patches_path=path,rodata_symbol='jtbl_8009FD00_game')
    obj=source.assemble(text,'bad-guard');assert source.payload(obj,source.NAME)==source.payload(source.OUT/'original.o',source.NAME)
   except(AssertionError,ValueError):count+=1
   else:raise AssertionError(('ineffective production guard control',label))
 for i in sorted(selected):
  for field in('expected','replacement','omitted'):
   changed=[dict(row)for row in rows]
   if field=='omitted':changed.pop(i)
   else:changed[i][field]='0x%08X'%(int(changed[i][field],0)^1)
   rejected(changed,(i,field))
 for i in inserted:
  for value in('', '0x%08X'%(int(rows[i]['insert_after'],0)^1)):
   changed=[dict(row)for row in rows];changed[i]['insert_after']=value;rejected(changed,(i,'insert_after',value))
 for kind,i in relocated.items():
  for field in('expected_relocations','replacement_relocations'):
   changed=[dict(row)for row in rows];changed[i][field]=kind+':actor_bound_invalid_binding';rejected(changed,(i,field))
 assert count==2*(3*len(selected)+2*len(inserted)+2*len(relocated))
 report=dict(passes=True,dual_padders=True,guard_rows=len(rows),selected_guard_families=len(selected),permutation_phase_examples=len(phase_examples),relocation_classes=sorted(relocated),insertion_controls=4,effective_padder_controls=count)
 (source.OUT/'guard-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report