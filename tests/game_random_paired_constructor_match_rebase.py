"""Link the target bodies at three independent code and data symbol bases."""
import subprocess
from tools.experiments import game_random_paired_constructor_match as packet
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions

def run(state):
 report={}
 for name in state:
  start=0x41c if name.endswith('60D8') else 0x45c;count=0
  for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
   symbols={f'D_800A{x:04X}':0x800a0000+x+0x11000*k for x in range(start,start+32,4)}
   symbols.update(func_150ADA20=0x150ada20+0x4000*k,func_150ADA68=0x150ada68+0x4000*k,func_151303BC=0x151303bc+0x8000*k,memcpy=0x10022ec0+0x1000*k)
   for key in ('after','retail','generated','generic'):
    ld=packet.OUT/(name+'-rebase-%d-%s.ld'%(k,key));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
    undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(state[name][key])],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
    for line in undefined:
     symbol=line.split()[-1]
     if symbol not in defined:defined[symbol]=0x800a6000 if symbol.startswith('D_') else 0x15008000
    cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%(n,v)for n,v in defined.items()],'-o',str(elf),str(state[name][key])]
    r=subprocess.run(cmd,cwd=packet.ROOT/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
    funcs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=funcs[name];raw,refs=packet.payload(state[name][key],name);expected=bound_blob(raw,refs,symbols)
    assert len(actual)>=len(expected) and tuple(actual[:len(expected)])==tuple(expected),(name,key,k);count+=1
  report[name]={'symbol_bases':3,'actual_gnu_links':count}
 return report
