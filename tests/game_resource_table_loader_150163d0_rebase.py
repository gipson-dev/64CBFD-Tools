import json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_resource_table_loader_150163d0_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
def main():
 NAME='func_150163D0';links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  symbols={'D_800D18B0':0x800D0000|low,'func_1502B7F0':0x15020000|(low&0xfffc)}
  for tag in ('padded_150163D0_generic','padded_150163D0_generated','original_150163D0'):
   path=out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};words=bound_blob(data[a:a+n],refs,symbols)
   script=out/('rebase_150163D0_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x150163D0 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr
   bin=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(bin)],capture_output=True,check=True);blob=bin.read_bytes();assert words==list(struct.unpack_from('>%dI'%len(words),blob));links+=1
 report=dict(gnu_rebased_links=links,guard_rows=52,independent_bindings=True,source_installed=False);(out/'rebase_150163D0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
