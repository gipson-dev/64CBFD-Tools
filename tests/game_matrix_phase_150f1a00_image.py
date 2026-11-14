"""Private actual Make and strict linked image with the caller ABI fix."""
from pathlib import Path
import inspect,json,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-matrix-phase-150f1a00-durable';q.out=q.p.out=out
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
    dest=frozen/name
    if not dest.exists():raise ValueError('Frozen pre-install image missing: '+name)
code=inspect.getsource(q.actual_make);needle="assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==1";assert code.count(needle)==1
code=code.replace(needle,"assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==2");scope=dict(q.actual_make.__globals__);exec(code,scope)
targets,commands=scope['actual_make']({'game/generated_11C2B0':out/'candidate.c','game/generated_61490':out/'caller-after.c'})
target=targets['game/generated_11C2B0'];caller=targets['game/generated_61490']
assert same_functions(root/'conker/build/src/game/generated_11C2B0.c.o',target,('func_150F1A00',))==43
assert normalized_pools(root/'conker/build/src/game/generated_11C2B0.c.o')==normalized_pools(target)
assert same_functions(root/'conker/build/src/game/generated_61490.c.o',caller)==10
assert normalized_pools(root/'conker/build/src/game/generated_61490.c.o')==normalized_pools(caller)
beforesec=sections(root/'conker/build/src/game/generated_61490.c.o');aftersec=sections(caller)
caller_sections=sorted(n for n in beforesec.keys()|aftersec.keys() if beforesec.get(n)!=aftersec.get(n))
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes()
truth=(root/'conker/conker.us.bin').read_bytes()[0x11eeb0:0x11eff8]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
code=code.replace(needle,"sizes={'func_150F1A00':328}");scope=dict(q.strict_image.__globals__);exec(code,scope)
image=scope['strict_image'](before,after,{'func_150F1A00':truth})
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_150F1A00'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'functions':len(b),'all_addresses_fixed':True,'image':image,'protected_data':data,
        'owner_neighbors_unchanged':43,'caller_functions_unchanged':10,'caller_sections_changed':caller_sections,'uncredited':True}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
