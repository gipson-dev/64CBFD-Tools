def run():
 from tools.experiments import game_hud_state_15178eb0_match as packet
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 from tools.tests.game_hud_state_15178eb0_oracle import S
 from tools.match_progress import load_elf_functions
 import subprocess
 root=packet.ROOT;out=packet.OUT;count=0
 for name in packet.NAMES:
  for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
   symbols={key:((base&0xf0000000)|(value&0x0fffffff))+0x1000*k if key.startswith('func_') else value+0x11000*k for key,value in S.items()}
   truth=bound_blob(*payload(out/('retail-'+name+'.o'),name),symbols)
   for key in ('after','retail-'+name,'generated','generic'):
    obj=out/(key+'.o');ld=out/('rebase-%s-%s-%d.ld'%(name,key,k));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
    undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();defined=dict(symbols)
    for line in undefined:
     sym=line.split()[-1]
     if sym not in defined:defined[sym]=0x800a6000 if sym.startswith('D_') else ((base&0xf0000000)|0x00008000)
    cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%(n,v) for n,v in defined.items()],'-o',str(elf),str(obj)]
    r=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr
    funcs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=funcs[name];expected=bound_blob(*payload(obj,name),symbols)
    assert len(actual)>=len(expected) and tuple(actual[:len(expected)])==tuple(expected),(name,key,k)
    if key!='after' or name==packet.NAMES[0]:assert tuple(expected)==tuple(truth),(name,key,k)
    count+=1
 print('GNU links',count,'across three layouts; direct and guarded outputs match rebased retail')
