from pathlib import Path
import subprocess,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
name='func_15156028';original=out/'durable-retail.o';raw,refs=payload(original,name);count=0
for k,low in enumerate((0,0x7ffc,0x8000,0xfffc)):
 symbols={'D_800CC2D0':0x80010000+low,'func_1516972C':0x15030000+k*0x100};expected=tuple(bound_blob(raw,refs,symbols))
 for obj in (original,out/'durable-generated.o',out/'durable-generic.o'):
  prefix=out/(obj.stem+'-layout-'+str(k));ld=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15001000+k*0x10000))
  names=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()]
  defs={n:symbols.get(n,0x800a6000 if n.startswith('D_') else 0x15008000) for n in names}
  p=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%x for x in defs.items()],'-o',str(elf),str(obj)],cwd=root/'conker',capture_output=True,text=True);assert p.returncode==0,p.stderr
  fs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert tuple(fs[name][:len(expected)])==expected,(obj,k);count+=1
print(count,'GNU links across four high/low symbol layouts; retail and both padded targets agree')
