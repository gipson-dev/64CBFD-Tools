from pathlib import Path
import subprocess,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-query-list-1509dbbc-screen'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.match_progress import load_elf_functions
name='func_1509DBBC';lookup={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};checks=0
for k,(base,rows,table) in enumerate(((0x15001000,0x800dce50,0x800a6060),(0x1f008000,0x80017ffc,0x80027ffc),(0x1000fff0,0x80028000,0x80038000))):
 syms=dict(lookup,D_800DCE50=rows,D_800A6060=table,func_150E36BC=(base&0xf0000000)|0x050e36bc)
 data,refs=payload(out/'retail.o',name);truth=tuple(bound_blob(data,refs,{n:syms[n] for es in refs.values() for _,n in es}))
 for objname in ('retail.o','generated.o','generic.o'):
  obj=out/objname;ld=out/('rebase-%s-%d.ld'%(obj.stem,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
  names=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()];definitions={n:syms.get(n,0x800a6000 if n.startswith('D_') else ((base&0xf0000000)|0x8000)) for n in names}
  cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%x for x in definitions.items()],'-o',str(elf),str(obj)];r=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
  functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert tuple(functions[name][:len(truth)])==truth,(objname,k);checks+=1
print(checks,'GNU links across three layouts: retail and both padded streams agree')
