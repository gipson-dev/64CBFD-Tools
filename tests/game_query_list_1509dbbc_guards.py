"""Reject corrupted target guard words and relocation preimages."""
import csv,io
from tools.experiments import game_query_list_1509dbbc_match as packet
from tools import pad_generated_object as pg
from tools import pad_c_object as pc

def run():
 root,out=packet.ROOT,packet.OUT;rows=[r for r in csv.DictReader(io.StringIO((out/'private-guards.csv').read_text())) if r['filename']=='generated_C9EC0'];fields=list(rows[0]);count=0
 for i,row in enumerate(rows):
  if row['function']!='func_1509DBBC':continue
  for kind in ('word','relocation'):
   altered=[dict(x) for x in rows];item=altered[i]
   if kind=='word':item['expected']=hex(int(item['expected'],0)^1)
   else:item['expected_relocations']='R_MIPS_32:__invalid_guard_symbol';item['replacement_relocations']='-'
   file=out/'corrupt-guard.csv'
   with file.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(altered)
   for mode in ('generated','generic'):
    try:
     if mode=='generated':pg.emit_padded_assembly(out/'selected2.o',root/'conker/asm/C9EC0.s',filename='generated_C9EC0',word_patches_path=file,rodata_symbol='jtbl_8009F1AC_game')
     else:pc.emit_padded_assembly(out/'selected2.o',root/'conker/retail_layout.us.txt','generated_C9EC0',word_patches_path=file,rodata_symbol='jtbl_8009F1AC_game')
    except ValueError as error:
     if 'func_1509DBBC' not in str(error):raise
    else:raise AssertionError((i,kind,mode))
    count+=1
 assert count==112,count
 print(count,'individual corrupted word and relocation preimages rejected across both padders')
