"""Test clock-alias guards at signed-low relocation carry boundaries."""
import subprocess
from tools.experiments import game_eeprom_poller_151dcfd8_match as packet
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.tests import game_eeprom_poller_151dcfd8_guest as guest
def run():
 name='func_151DCFD8';out=packet.OUT;raw_mismatches=0
 for k,(base,clock) in enumerate(((0x15001000,0x80017ffc),(0x1f008000,0x8001fff8),(0x1000fff0,0x80028000))):
  symbols=dict(guest.SYMS,D_8002BD10=clock,D_8002BD14=clock+4)
  for n in ('osRecvMesg','func_151DD4E0','__ll_mul','__ull_div','osSetTimer'):symbols[n]=(base&0xf0000000)|(symbols[n]&0x0fffffff)
  truth=bound_blob(*payload(out/'retail.o',name),symbols)
  for key in ('after','retail','generated','generic'):
   obj=out/(key+'.o');ld=out/('rebase-%s-%d.ld'%(key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
   undef=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
   for line in undef:
    sym=line.split()[-1]
    if sym not in defined:defined[sym]=0x800a6000 if sym.startswith('D_') else ((base&0xf0000000)|0x8000)
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%item for item in defined.items()],'-o',str(elf),str(obj)]
   r=subprocess.run(cmd,cwd=packet.ROOT/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
   functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');linked=tuple(functions[name][:len(truth)])
   if key=='after':raw_mismatches+=linked!=tuple(truth)
   else:assert linked==tuple(truth),(key,k)
 assert raw_mismatches==0,('raw alias mismatch at tested layouts',raw_mismatches)
 print('12 rebased links across three layouts; guarded and raw target streams match retail at tested clock boundaries')
