"""Exercise every target relocation through GNU links at three symbol bases."""
import struct,subprocess
from tools.experiments import game_paired_height_descriptor_screen as packet
from tools.tests import game_paired_height_descriptor_oracle as guest
from tools.match_progress import load_elf_functions

def run(state):
 report={}
 for name in state:
  first=name.endswith('5F94');offset=0x410 if first else 0x450;count=0
  for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
   symbols={f'D_800A{x:04X}':0x800a0000+x+0x11000*k for x in range(offset,offset+12,4)}
   symbols.update(func_15045800=0x15045800+0x4000*k,func_1513418C=0x1513418c+0x8000*k,memcpy=0x10022ec0+0x1000*k)
   for key in ('after','retail','generated','generic'):
    ld=packet.OUT/(name+'-rebase-%d-%s.ld'%(k,key));elf=ld.with_suffix('.elf')
    ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
    undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(state[name][key])],capture_output=True,text=True,check=True).stdout.splitlines()
    defined=dict(symbols)
    for line in undefined:
     symbol=line.split()[-1]
     if symbol not in defined:defined[symbol]=0x800a6000 if symbol.startswith('D_') else 0x15008000
    cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,
         *['--defsym=%s=0x%X'%(n,v) for n,v in defined.items()],'-o',str(elf),str(state[name][key])]
    r=subprocess.run(cmd,cwd=packet.ROOT/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
    functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=functions[name]
    expected=guest.blob(state[name][key],name,symbols)
    assert len(actual)>=len(expected) and tuple(actual[:len(expected)])==tuple(expected),(name,key,k,len(actual),len(expected));count+=1
  report[name]={'symbol_bases':3,'actual_gnu_links':count}
 return report
