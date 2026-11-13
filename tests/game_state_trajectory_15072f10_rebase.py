import subprocess
from pathlib import Path
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.match_progress import load_elf_functions
from importlib.machinery import SourceFileLoader
from tools.tests import game_state_trajectory_15072f10_oracle as o
from tools.experiments import game_state_trajectory_15072f10_match as packet
def run():
 root=packet.ROOT;out=packet.OUT;name='func_15072F10';count=0
 for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
  symbols={key:value+(0x11000*k if key.startswith('D_800') else 0x4000*k)for key,value in o.SYMS.items()}
  for key in ('after','retail','generated','generic'):
   obj=out/(key+'.o');ld=out/('rebase-%s-%d.ld'%(key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
   undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
   for line in undefined:
    symbol=line.split()[-1]
    if symbol not in defined:defined[symbol]=0x800a6000 if symbol.startswith('D_') else 0x15008000
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%(n,v)for n,v in defined.items()],'-o',str(elf),str(obj)]
   r=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
   funcs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=funcs[name];raw,refs=payload(obj,name);expected=bound_blob(raw,refs,symbols)
   assert len(actual)>=len(expected) and tuple(actual[:len(expected)])==tuple(expected),(key,k);count+=1
 print('GNU links',count,'independent symbol bases',3)
