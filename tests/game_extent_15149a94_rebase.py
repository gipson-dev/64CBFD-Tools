from pathlib import Path
import subprocess,sys
from tools.experiments import game_extent_15149a94_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
def run():
 name='func_15149A94'
 for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
  symbols={'D_800A578C':0x800A578C+k*0x10000,'D_800A5790':0x800A5790+k*0x10000,'func_1513F680':((base&0xf0000000)|0x0133f680)+k*0x1000}
  truth=bound_blob(*payload(out/'retail.o',name),symbols)
  for key in ('after','retail','generated','generic'):
   obj=out/(key+'.o');ld=out/('rebase-%s-%d.ld'%(key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
   undef=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
   for line in undef:
    sym=line.split()[-1]
    if sym not in defined:defined[sym]=0x800a6000 if sym.startswith('D_') else ((base&0xf0000000)|0x8000)
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%item for item in defined.items()],'-o',str(elf),str(obj)]
   r=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
   functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');expected=bound_blob(*payload(obj,name),symbols);assert tuple(functions[name][:len(expected)])==tuple(expected)==tuple(truth),(key,k)
 print('12 rebased links across 3 layouts preserve retail target and bindings')
