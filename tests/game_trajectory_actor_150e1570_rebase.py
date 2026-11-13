def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_trajectory_actor_150e1570_match as packet
 root=packet.ROOT;out=packet.OUT;name='func_150E1570'
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 from tools.match_progress import load_elf_functions
 syms=dict(D_800CC2D0=0x800cc2d0,D_800C3E78=0x800c3e78,func_15047390=0x15047390,func_15049440=0x15049440,func_1505D1C4=0x1505d1c4);count=0
 for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
  symbols={key:value+(0x11000*k if key.startswith('D_') else 0x4000*k) for key,value in syms.items()}
  for key in ('after','retail','generated','generic'):
   obj=out/(key+'.o');ld=out/('rebase-%s-%d.ld'%(key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%(n,v) for n,v in symbols.items()],'-o',str(elf),str(obj)]
   r=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
   funcs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=funcs[name];data,refs=payload(obj,name);expected=bound_blob(data,refs,symbols);assert len(actual)>=len(expected) and tuple(actual[:len(expected)])==tuple(expected),(key,k);count+=1
 print('GNU links',count,'independent symbol bases 3')
