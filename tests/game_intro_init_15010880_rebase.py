"""Independently GNU-link the original and padded initializer at four layouts."""
from pathlib import Path
import json,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-intro-init-15010880-durable';name='func_15010880'
base={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def link(obj,target,defs,label):
 _,fs,_=parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
 script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 u=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in u if line.split()]
 assert set(names)<=set(defs),(obj,set(names)-set(defs))
 argv=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',f'{n}={hex(defs[n])}')],'-o',str(elf),str(obj)]
 p=subprocess.run(argv,capture_output=True,text=True);assert p.returncode==0,p.stderr
 subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()[offset:offset+336]
layouts=((0x15010880,0x800d3098),(0x17107ffc,0x80107ffc),(0x1910fff0,0x8020fffc),(0x1b10fff0,0x80318000));results=[]
for i,(target,address) in enumerate(layouts):
 defs=dict(base);defs.update(D_800D3098=address,D_800E0934=address+0x10040,D_800D2E4C=address+0x20080)
 for j,n in enumerate(('func_150DE32C','func_15177410','func_15149130','memcpy')):defs[n]=(target&0xf0000000)+0x10000+0x8000*j+0x7ffc
 a=link(out/'retail.o',target,defs,f'rebase-{i}-retail');b=link(out/'padded.o',target,defs,f'rebase-{i}-padded');assert a==b,(i,target,address);results.append(dict(entry=hex(target),resource=hex(address)))
report={'layouts':results,'gnu_links':8,'normalized_equals_retail':True,'hi16_low_half_carry_tested':True};(out/'rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
