"""Check guarded and retail code at four independent table layouts."""
from pathlib import Path
import json,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable';conker=root/'conker';name='func_151ED29C'
base={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
def link(obj,target,defs,label):
    _,functions,_=parse_object(obj);offset=functions[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
    lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()]
    assert set(names)<=set(defs),set(names)-set(defs)
    args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)]
    p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr
    subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
    return binary.read_bytes()[offset:offset+404]
layouts=((0x151ed29c,0x8009deb0),(0x17107ffc,0x80107ffc),(0x1910fff0,0x8020fffc),(0x1b10fff0,0x80318000));results=[]
for i,(target,table) in enumerate(layouts):
    defs=dict(base)
    for off in (0,4,8,12):defs['D_%08X'%(0x8009deb0+off)]=table+off
    a=link(out/'retail.o',target,defs,f'rebase-{i}-retail');b=link(out/'guarded.o',target,defs,f'rebase-{i}-guarded')
    assert a==b,(i,hex(target),hex(table));results.append({'entry':hex(target),'tables':hex(table)})
report={'gnu_links':8,'layouts':results,'guarded_equals_retail':True,'uncredited':True}
(out/'rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
