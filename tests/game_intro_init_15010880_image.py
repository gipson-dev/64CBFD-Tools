from pathlib import Path
import inspect,json,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-intro-init-15010880-durable';q.out=out;q.p.out=out
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
 dest=frozen/name
 if not dest.exists():raise ValueError('Frozen pre-install image missing: '+name)
targets,commands=q.actual_make({'game_3DC30':out/'typed-proposal.c'});target=targets['game_3DC30']
assert same_functions(root/'conker/build/src/game_3DC30.c.o',target,('func_15010880',))==2
assert normalized_pools(root/'conker/build/src/game_3DC30.c.o')==normalized_pools(target)
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();actual=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x3dd30:0x3de80]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
code=code.replace(needle,"sizes={'func_15010880':336}");ns=dict(q.strict_image.__globals__);exec(code,ns);image=ns['strict_image'](before,actual,{'func_15010880':truth})
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_15010880'}
protected=audit_layout(elf,root/'conker');assert protected['exact'] and protected['different_bytes']==0
report={'commands':len(commands),'functions':len(b),'all_addresses_fixed':True,'image':image,'protected_data':protected,'owner_neighbors_unchanged':2}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
