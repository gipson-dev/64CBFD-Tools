"""Private actual-Make and full-ELF audit with the adjacent table base."""
from pathlib import Path
import inspect,json,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable';q.out=q.p.out=out
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
    dest=frozen/name
    if not dest.exists():raise ValueError('Frozen pre-install image missing: '+name)
code=inspect.getsource(q.actual_make)
needle="parts=[replacements.get(a,a)for a in parts]"
assert code.count(needle)==1
code=code.replace(needle,"replacements['jtbl_800AB9BC']='jtbl_800AB994';"+needle)
scope=dict(q.actual_make.__globals__);exec(code,scope)
targets,commands=scope['actual_make']({'game/generated_20AE20':out/'alias-00.c'})
assert any('--rodata-symbol jtbl_800AB994' in c for c in commands),commands
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes()
truth=(root/'conker/conker.us.bin').read_bytes()[0x20f76c:0x20f8b4]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
code=code.replace(needle,"sizes={'func_151E22BC':328}");scope=dict(q.strict_image.__globals__);exec(code,scope)
image=scope['strict_image'](before,after,{'func_151E22BC':truth})
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump')
b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_151E22BC'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'functions':len(b),'all_addresses_fixed':True,'image':image,'protected_data':data,
        'table_base_changed_to_original_earlier_table':True,'uncredited':True}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
