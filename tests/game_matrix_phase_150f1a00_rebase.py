"""Compare original and padded code over four rebased address layouts."""
from pathlib import Path
import json,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-matrix-phase-150f1a00-durable';conker=root/'conker';name='func_150F1A00'
base={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
def link(obj,target,defs,label):
    _,functions,_=parse_object(obj);offset=functions[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
    lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()]
    assert set(names)<=set(defs),set(names)-set(defs)
    args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)]
    p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr
    subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
    return binary.read_bytes()[offset:offset+328]
layouts=((0x150f1a00,0x80088b00,0x800cc298,0x800be9e4,0x800a18e8),(0x17107ffc,0x80107ffc,0x80207ffc,0x80307ffc,0x80407ffc),
         (0x1910fff0,0x8010fffc,0x8020fffc,0x8030fffc,0x8040fffc),(0x1b10fff0,0x80118000,0x80218000,0x80318000,0x80418000));results=[]
for i,(target,rates,state,ticks,bounds) in enumerate(layouts):
    defs=dict(base,D_80088B00=rates,D_800CC298=state,D_800BE9E4=ticks,D_800A18E8=bounds,D_800A18EC=bounds+4,D_800A18F0=bounds+8,cosf=(target&0xf0000000)|0x01047c00)
    a=link(out/'retail.o',target,defs,f'rebase-{i}-retail');b=link(out/'generated-guarded.o',target,defs,f'rebase-{i}-guarded')
    assert a==b,(i,hex(target));results.append({'entry':hex(target),'state':hex(state),'ticks':hex(ticks),'bounds':hex(bounds)})
report={'gnu_links':8,'layouts':results,'guarded_equals_retail':True,'uncredited':True}
(out/'rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
