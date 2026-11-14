"""Actual-Make private shadow and independently predicted whole ELF."""
from pathlib import Path
import inspect,json,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-timed-motion-150f48d0-durable';q.out=q.p.out=out
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
 dest=frozen/name
 if not dest.exists():raise ValueError('Frozen pre-install image missing: '+name)
targets,commands=q.actual_make({'game/generated_121A20':out/'formatted.c'})
target=targets['game/generated_121A20'];base=root/'conker/build/src/game/generated_121A20.c.o'
assert same_functions(base,target,('func_150F48D0',))==5 and normalized_pools(base)==normalized_pools(target)
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x121d80:0x121ee8]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
scope=dict(q.strict_image.__globals__);exec(code.replace(needle,"sizes={'func_150F48D0':360}"),scope)
image=scope['strict_image'](before,after,{'func_150F48D0':truth})
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_150F48D0'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'owner_neighbors':5,'functions':len(a),'all_addresses_fixed':True,'image':image,'protected_data':data,'uncredited':True}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
