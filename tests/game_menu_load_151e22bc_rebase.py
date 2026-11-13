"""GNU-link retail and private padded functions at independent layouts."""
from pathlib import Path
import json,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable';name='func_151E22BC'
base={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def link(obj,target,defs,label):
    _,fs,_=parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
    u=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()
    names=[line.split()[-1] for line in u if line.split()]
    assert set(names)<=set(defs),(obj,set(names)-set(defs))
    argv=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',f'{n}={hex(defs[n])}')],'-o',str(elf),str(obj)]
    p=subprocess.run(argv,capture_output=True,text=True);assert p.returncode==0,p.stderr
    subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
    return binary.read_bytes()[offset:offset+328]
layouts=((0x151e22bc,0x800ab994),(0x17107ffc,0x80107ffc),(0x1910fff0,0x8020fffc),(0x1b10fff0,0x80318000));results=[]
for i,(target,address) in enumerate(layouts):
    defs=dict(base);defs.update(jtbl_800AB994=address,D_800E0BE0=address+0x10040,D_8008FDD4=address+0x20080,
                               D_800AB690=address+0x300c0,D_80082BBC=address+0x400f0)
    # The called placeholder is defined in the same padded owner and therefore
    # moves with it; the isolated retail object needs the corresponding symbol.
    defs['func_151DD9E4']=target-(0x151e22bc-0x151dd9e4)
    a=link(out/'retail.o',target,defs,f'rebase-{i}-retail');b=link(out/'guarded-private.o',target,defs,f'rebase-{i}-guarded')
    assert a==b,(i,hex(target),hex(address));results.append({'entry':hex(target),'table':hex(address)})
report={'layouts':results,'gnu_links':8,'guarded_equals_retail':True,'uncredited':True}
(out/'rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
