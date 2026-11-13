def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_actor_sentinel_query_15037880_match as packet
 root=packet.ROOT;out=packet.OUT;name='func_15037880'
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 from tools.match_progress import load_elf_functions
 syms=dict(D_800CC2D0=0x800cc2d0,D_800DBFF0=0x800dbff0,D_800C3FF4=0x800c3ff4,D_8009862C=0x8009862c);count=0
 for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
  symbols={key:value+0x11000*k for key,value in syms.items()}
  for key in ('after','retail','generated','generic'):
   obj=out/(key+'.o');ld=out/('rebase-%s-%d.ld'%(key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
   undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
   for line in undefined:
    symbol=line.split()[-1]
    if symbol not in defined:defined[symbol]=0x800a6000 if symbol.startswith('D_') else 0x15008000
   cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%(n,v) for n,v in defined.items()],'-o',str(elf),str(obj)]
   r=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
   funcs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=funcs[name];data,refs=payload(obj,name);expected=bound_blob(data,refs,symbols);assert len(actual)>=len(expected) and tuple(actual[:len(expected)])==tuple(expected),(key,k);count+=1
 print('GNU links',count,'independent symbol bases 3')
