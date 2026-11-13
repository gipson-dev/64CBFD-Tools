"""Verify guarded relocation bindings across independent link layouts."""
import subprocess
from tools.experiments import game_coordinate_table_1512abf8_match as packet
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
def run():
 name='func_1512ABF8';out=packet.OUT
 for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
  symbols={n:0x80000000+v+k*0x10000 for n,v in (('D_80089590',0x89590),('D_800DC200',0xdc200),('D_800DC0C0',0xdc0c0),('D_80082FA0',0x82fa0),('D_800BE9F0',0xbe9f0))}
  symbols['bzero']=((base&0xf0000000)|0x000226f0)+k*0x1000
  truth=bound_blob(*payload(out/'retail.o',name),symbols)
  for key in ('after','retail','generated','generic'):
   obj=out/(key+'.o');ld=out/('rebase-%s-%d.ld'%(key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
   undef=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
   for line in undef:
    sym=line.split()[-1]
    if sym not in defined:defined[sym]=0x800a6000 if sym.startswith('D_') else ((base&0xf0000000)|0x8000)
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%item for item in defined.items()],'-o',str(elf),str(obj)]
   r=subprocess.run(cmd,cwd=packet.ROOT/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
   functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');expected=bound_blob(*payload(obj,name),symbols);assert tuple(functions[name][:len(expected)])==tuple(expected),(key,k)
   if key!='after':assert tuple(expected)==tuple(truth),(key,k)
 print('12 rebased links; retail and both guarded streams agree across three layouts')
