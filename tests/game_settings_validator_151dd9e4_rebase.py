"""Link the extracted retail and guarded bodies at four data layouts."""
from pathlib import Path
import json,re,struct,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-settings-validator-151dd9e4-durable';conker=root/'conker';name='func_151DD9E4'
full=(conker/'asm/20AE20.s').read_text();match=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',full,re.M|re.S);assert match
asm=out/'retail.s';retail=out/'retail.o';asm.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+name+',.-'+name+'\n')
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(retail.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
base={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
def link(obj,target,defs,label):
    _,functions,_=parse_object(obj);offset=functions[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
    lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()]
    assert set(names)<=set(defs),set(names)-set(defs)
    args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)]
    p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr
    subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
    return binary.read_bytes()[offset:offset+432]
layouts=((0x151dd9e4,0x800e0be0,0x8008fe54),(0x17107ffc,0x80107ffe,0x80207ffe),(0x1910fff0,0x8020fffc,0x8030fffc),(0x1b10fff0,0x80318000,0x80418000));results=[]
for i,(target,settings,table) in enumerate(layouts):
    defs=dict(base)
    for n in range(4):defs['D_%08X'%(0x800e0be0+n)]=settings+n
    for n in (0,1,2,3,24,25,26,27,48,49,50):defs['D_%08X'%(0x8008fe54+n)]=table+n
    a=link(retail,target,defs,f'rebase-{i}-retail');b=link(out/'generated-guarded.o',target,defs,f'rebase-{i}-guarded')
    assert a==b,(i,hex(target))
    results.append({'entry':hex(target),'settings':hex(settings),'tables':hex(table)})
report={'gnu_links':8,'layouts':results,'guarded_equals_retail':True,'uncredited':True}
(out/'rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
