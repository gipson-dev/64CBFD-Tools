from pathlib import Path
import inspect,json,shutil,hashlib
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-viewport-helper-shape-screen';q.out=q.p.out=out;q.root=q.p.root=root;frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
 src=root/'conker/build'/name;dest=frozen/name
 if not dest.exists():shutil.copyfile(src,dest)
 assert hashlib.sha256(dest.read_bytes()).digest()==hashlib.sha256(src.read_bytes()).digest(),name
targets,commands=q.actual_make({'game/generated_138520':out/'owner-candidate.c'});target=targets['game/generated_138520'];base=root/'conker/build/src/game/generated_138520.c.o';assert same_functions(base,target,('func_1510B7B4',))==13 and normalized_pools(base)==normalized_pools(target)
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x138c64:0x138e08]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1 and code.count('r[2][2]==12')==1
scope=dict(q.strict_image.__globals__);exec(code.replace(needle,"sizes={'func_1510B7B4':420}").replace('r[2][2]==12','r[2][2]==412'),scope);image=scope['strict_image'](before,after,{'func_1510B7B4':truth});assert image['strict_exclusions']==0
old,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');new,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys() and oa==ob and {n for n in old if old[n]!=new[n]}=={'func_1510B7B4'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'neighbors':13,'functions':len(old),'all_addresses_fixed':True,'image':image,'protected_data':data,'old_elf_sha256':hashlib.sha256(before).hexdigest(),'candidate_elf_sha256':hashlib.sha256(after).hexdigest(),'uncredited':True};(out/'image.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
