from pathlib import Path
import subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.match_progress import load_elf_functions
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT;name='func_1517ABB0';generic=out/'generic.o'
r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(generic),str(out/'generic.s')],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
raw,refs=payload(out/'retail.o',name);assert payload(generic,name)==(raw,refs)
assert same_functions(root/'conker/build/src/game/generated_1A8060.c.o',generic,(name,))==1
count=0
for k,low in enumerate((0,0x7ffc,0x8000,0xfffc)):
 symbols={'D_800DD460':0x80010000+low,'D_800A7230':0x80030000+low,'D_800C4310':0x80050000+low,'func_10004074':0x10024000+k*0x100}
 for obj in (out/'retail.o',out/'padded.o',generic):
  prefix=out/(obj.stem+'-layout-'+str(k));ld=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15001000+k*0x10000))
  names=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()]
  defs={n:symbols.get(n,0x800A6000 if n.startswith('D_') else 0x15008000) for n in names}
  p=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%x for x in defs.items()],'-o',str(elf),str(obj)],cwd=root/'conker',capture_output=True,text=True);assert p.returncode==0,p.stderr
  listing=subprocess.run(['mips-linux-gnu-nm','-n',str(elf)],capture_output=True,text=True,check=True).stdout;linked={parts[2]:int(parts[0],16) for line in listing.splitlines() if len(parts:=line.split())==3}
  assert all(linked[n]==v for n,v in symbols.items());expected=tuple(bound_blob(raw,refs,linked));fs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert tuple(fs[name][:len(expected)])==expected,(obj,k)
  count+=1
print(count,'GNU links across four symbol layouts agree for retail and both padders',flush=True)
