"""Private actual-Make and independently predicted complete ELF."""
from pathlib import Path
import inspect,json,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-crossing-150e6230-durable';q.out=q.p.out=out
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
 dest=frozen/name
 if not dest.exists():shutil.copyfile(root/'conker/build'/name,dest)
 expected={'conker.ld':'6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5','conker.us.elf':'058f88114ae93f5fa9a271c240f4c0be1afcf68769fd51e3cb646c977cbde195'}[name]
 assert __import__('hashlib').sha256(dest.read_bytes()).hexdigest()==expected and __import__('hashlib').sha256((root/'conker/build'/name).read_bytes()).hexdigest()==expected
targets,commands=q.actual_make({'game/generated_113480':out/'formatted.c'})
target=targets['game/generated_113480'];base=root/'conker/build/src/game/generated_113480.c.o'
assert same_functions(base,target,('func_150E6230',))==4 and normalized_pools(base)==normalized_pools(target)
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x1136e0:0x113850]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
scope=dict(q.strict_image.__globals__);exec(code.replace(needle,"sizes={'func_150E6230':368}"),scope)
image=scope['strict_image'](before,after,{'func_150E6230':truth});assert image=={'changed_bytes':270,'metadata_groups':[],'strict_exclusions':0}
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_150E6230'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'owner_neighbors':4,'functions':len(a),'all_addresses_fixed':True,'image':image,'protected_data':data,'uncredited':True}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
