"""Link original and guarded linked-effect bodies at four layouts."""
from pathlib import Path
import json,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable';conker=root/'conker';name='func_151D2C40'
asm=(conker/'asm/nonmatchings/game_1FFF60/func_151D2C40.s').read_text()
retailasm=out/'retail.s';retail=out/'retail.o'
retailasm.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'\n.size '+name+',.-'+name+'\n')
argv=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(retail.relative_to(conker)),str(retailasm.relative_to(conker))]
p=subprocess.run(argv,cwd=conker,capture_output=True,text=True);assert not p.returncode,p.stderr
base={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
def link(obj,target,defs,label):
    _,fs,_=parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
    u=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[l.split()[-1] for l in u if l.split()]
    assert set(names)<=set(defs),(obj,set(names)-set(defs))
    argv=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',f'{n}={hex(defs[n])}')],'-o',str(elf),str(obj)]
    p=subprocess.run(argv,capture_output=True,text=True);assert not p.returncode,p.stderr
    subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
    return binary.read_bytes()[offset:offset+364]
layouts=((0x151d2c40,0x8008fc40),(0x17107ffc,0x80107ffc),(0x1910fff0,0x8020fffc),(0x1b10fff0,0x80318000));results=[]
for i,(target,table) in enumerate(layouts):
    defs=dict(base);defs.update(D_8008FC40=table,D_8008FC48=table+8,D_800BE9E4=table+0x10040)
    a=link(retail,target,defs,f'rebase-{i}-retail');b=link(out/'guarded.o',target,defs,f'rebase-{i}-guarded')
    assert a==b,(i,hex(target),hex(table));results.append({'entry':hex(target),'callback_table':hex(table)})
report={'gnu_links':8,'layouts':results,'guarded_equals_retail':True,'uncredited':True}
(out/'rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
