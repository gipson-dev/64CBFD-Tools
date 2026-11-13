from pathlib import Path
import subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;name='func_1500E738';raw,refs=payload(out/'retail.o',name);count=0
for k,low in enumerate((0,0x7ffc,0x8000,0xfffc)):
 symbols={'D_80082FA0':0x80010000+low,'D_8008FD8C':0x80030000+low,'D_800DCA20':0x80050000+low,'D_800DCA24':0x80060000+low,'D_800DCA28':0x80070000+low,'D_800DCA2C':0x80080000+low,'jtbl_800961D0_game':0x80090000+low}
 for obj in (out/'retail.o',out/'padded.o'):
  prefix=out/(obj.stem+'-layout-'+str(k));ld=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15001000+k*0x10000))
  names=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()]
  defs={n:symbols.get(n,0x800A6000 if n.startswith('D_') else 0x15008000) for n in names}
  p=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%x for x in defs.items()],'-o',str(elf),str(obj)],cwd=root/'conker',capture_output=True,text=True);assert p.returncode==0,p.stderr
  listing=subprocess.run(['mips-linux-gnu-nm','-n',str(elf)],capture_output=True,text=True,check=True).stdout;linked={parts[2]:int(parts[0],16) for line in listing.splitlines() if len(parts:=line.split())==3}
  assert all(linked[n]==v for n,v in symbols.items());expected=tuple(bound_blob(raw,refs,linked));fs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert tuple(fs[name][:len(expected)])==expected,(obj,k)
  count+=1
print(count,'GNU links across four symbol layouts agree with retail',flush=True)
