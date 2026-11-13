"""Each private word and relocation preimage must fail closed in both padders."""
import csv,io
from tools.experiments import game_camera_query_150be850_match as packet
from tools import pad_generated_object as pg
from tools import pad_c_object as pc

def run():
 root,out=packet.ROOT,packet.OUT;owners={'game_C8950','generated_EBD00',*[x.rsplit('/',1)[1] for x in packet.STUBS]};rows=[r for r in csv.DictReader(io.StringIO((out/'query-private-guards.csv').read_text())) if r['filename'] in owners];fields=list(rows[0]);checks=0
 targets=[('func_1509BE40','game_C8950','query-shape08.o',out/'query-synthetic-retail.s'),('func_150BE850','generated_EBD00','abi.o',root/'conker/asm/EBD00.s')]
 indices={name:i for i,name in enumerate(packet.MANIFEST['sources'])}
 for path,function in packet.STUBS.items():
  owner=path.rsplit('/',1)[1];targets.append((function,owner,'packet-%d-after.o'%indices[path],root/('conker/asm/'+owner.removeprefix('generated_')+'.s')))
 for function,owner,obj,layout in targets:
  for index,row in enumerate(rows):
   if row['function']!=function:continue
   for kind in ('word','relocation'):
    altered=[dict(x) for x in rows];item=altered[index]
    if kind=='word':item['expected']=hex(int(item['expected'],0)^1)
    else:item['expected_relocations']='R_MIPS_32:__invalid_guard_symbol';item['replacement_relocations']='-'
    file=out/'corrupt-query-guard.csv'
    with file.open('w',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(altered)
    for mode in ('generic','generated'):
     try:
      if mode=='generic':pc.emit_padded_assembly(out/obj,root/'conker/retail_layout.us.txt',owner,word_patches_path=file)
      else:pg.emit_padded_assembly(out/obj,layout,filename=owner,word_patches_path=file)
     except ValueError as error:
      if function not in str(error):raise
     else:raise AssertionError((function,index,kind,mode))
     checks+=1
 print(checks,'individual corrupted word and relocation preimages rejected across both padders')
