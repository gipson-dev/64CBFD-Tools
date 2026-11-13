"""Rebind the original and padded scripts at independent MIPS symbol layouts."""
import subprocess
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions

root,out=source.ROOT,source.OUT
raw,refs=payload(out/'durable-retail.o',source.NAME);count=0
for k,low in enumerate((0,0x7ffc,0x8000,0xfffc)):
 symbols={'D_800D2E4C':0x80010000+low,'D_8003C8E0':0x80030000+low,
          'func_1509B704':0x15020000+k*0x100,'func_1509B8FC':0x15021000+k*0x100,
          'func_1509B810':0x15022000+k*0x100,'func_150ADAF0':0x15023000+k*0x100,
          'bzero':0x10024000+k*0x100}
 for obj in (out/'durable-retail.o',out/'durable-padded.o'):
  prefix=out/(obj.stem+'-layout-'+str(k));ld=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
  ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15001000+k*0x10000))
  names=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()]
  defs={n:symbols.get(n,0x800A6000 if n.startswith('D_') else 0x15008000) for n in names}
  p=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',source.NAME,*['--defsym=%s=0x%X'%x for x in defs.items()],'-o',str(elf),str(obj)],cwd=root/'conker',capture_output=True,text=True)
  assert p.returncode==0,p.stderr
  listing=subprocess.run(['mips-linux-gnu-nm','-n',str(elf)],capture_output=True,text=True,check=True).stdout
  linked={parts[2]:int(parts[0],16) for line in listing.splitlines() if len(parts:=line.split())==3}
  assert all(linked[n]==symbols[n] for n in ('D_800D2E4C','D_8003C8E0','func_150ADAF0','bzero'))
  expected=tuple(bound_blob(raw,refs,linked))
  fs,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump');actual=tuple(fs[source.NAME][:len(expected)])
  assert actual==expected,(obj,k,[(hex(i*4),hex(a),hex(b)) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:12],len(actual),len(expected))
  count+=1
print(count,'GNU links across four symbol layouts agree with retail',flush=True)
