"""Link original and guarded targets independently at several symbol layouts."""
import subprocess
from tools.experiments import game_camera_query_150be850_match as packet
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions

def run():
 root,out=packet.ROOT,packet.OUT;lookup={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};checks=0
 for name,original,variants in (('func_1509BE40','query-retail.o',('query-generic.o','query-generated.o')),('func_150BE850','retail.o',('generic.o','generated.o'))):
  for k,(base,global_base) in enumerate(((0x15001000,0x80012f60),(0x15008000,0x80017ffc),(0x1500fff0,0x80028000))):
   symbols=dict(lookup,D_800D2F60=global_base,D_800D2F64=global_base+4,D_800A00B0=global_base,D_800A00B4=global_base+4)
   raw,refs=payload(out/original,name);truth=tuple(bound_blob(raw,refs,{n:symbols[n] for entries in refs.values() for _,n in entries}))
   for objname in (original,*variants):
    obj=out/objname;tag=name+obj.stem+str(k);ld=out/(tag+'.ld');elf=out/(tag+'.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
    names=[line.split()[-1] for line in subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()]
    definitions={n:symbols.get(n,0x800a6000 if n.startswith('D_') else 0x15008000) for n in names}
    cmd=['mips-linux-gnu-ld','-m','elf32btsmip','--unresolved-symbols=ignore-all','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(obj)]
    result=subprocess.run(cmd,cwd=root/'conker',capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stderr)
    functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if tuple(functions[name][:len(truth)])!=truth:raise ValueError(('rebase mismatch',name,objname,k))
    checks+=1
 print(checks,'GNU links across three address layouts; original and both padded targets agree')
