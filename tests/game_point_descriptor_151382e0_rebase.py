from pathlib import Path
import subprocess,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
name='func_15153F18';source=(root/'conker/asm/17CAF0.s').read_text();a=source.index('glabel '+name);b=source.index('endlabel '+name,a)+len('endlabel '+name)
asm=out/'interface-helper-retail.s';original=asm.with_suffix('.o');asm.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+source[a:b]+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(original),str(asm)],cwd=root/'conker',check=True,capture_output=True)
lookup={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};count=0
for name,reference,variants in (('func_151382E0',out/'durable-retail.o',(out/'durable-point-padded.o',)),('func_15153F18',original,(out/'durable-helper-generated.o',out/'durable-helper-padded.o'))):
 raw,refs=payload(reference,name);names=sorted({n for entries in refs.values() for _,n in entries})
 for k,low in enumerate((0x2f60,0x7ffc,0x8000)):
  symbols=dict(lookup)
  for i,n in enumerate(names):symbols[n]=(0x80010000+i*0x10000+low if n.startswith('D_') else 0x15010000+i*0x100)
  expected=tuple(bound_blob(raw,refs,{n:symbols[n] for n in names}))
  for path in (reference,*variants):
   tag=name+'-'+path.stem+'-'+str(k);ld=out/(tag+'.ld');elf=out/(tag+'.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15001000+k*0x7000))
   undefined=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(path)],capture_output=True,text=True,check=True).stdout.splitlines()]
   definitions={n:symbols.get(n,0x800a6000 if n.startswith('D_') else 0x15008000) for n in undefined}
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(path)]
   p=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert p.returncode==0,p.stderr
   functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert tuple(functions[name][:len(expected)])==expected,(name,path,k);count+=1
print(count,'GNU relocation links across three low-half layouts for point and trail helper')
