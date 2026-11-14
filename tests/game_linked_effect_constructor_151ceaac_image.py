"""Check actual owner/caller Make and predict every linked-image byte."""
from pathlib import Path
import inspect,json,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-linked-effect-constructor-151ceaac-durable';q.out=q.p.out=out
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name in ('conker.ld','conker.us.elf'):
 dest=frozen/name
 if not dest.exists():raise ValueError('Frozen pre-install image missing: '+name)
shutil.copyfile(root/'conker/retail_word_patches.us.csv',out/'proposed-guards.csv')
code=inspect.getsource(q.actual_make);needle="assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==1";assert code.count(needle)==1
code=code.replace(needle,"assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==2");scope=dict(q.actual_make.__globals__);exec(code,scope)
targets,commands=scope['actual_make']({'game/generated_1FA770':out/'formatted.c','game/generated_97AA0':out/'caller-after.c'})
target=targets['game/generated_1FA770'];caller=targets['game/generated_97AA0'];base=root/'conker/build/src/game/generated_1FA770.c.o';callerbase=root/'conker/build/src/game/generated_97AA0.c.o'
assert same_functions(base,target,('func_151CEAAC',))==51 and normalized_pools(base)==normalized_pools(target)
assert same_functions(callerbase,caller)==16 and normalized_pools(callerbase)==normalized_pools(caller)
a,b=sections(callerbase),sections(caller);caller_sections=sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k))
assert set(caller_sections)<={'.mdebug'},caller_sections
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x1fbf5c:0x1fc0c0]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
code=code.replace(needle,"sizes={'func_151CEAAC':356}");scope=dict(q.strict_image.__globals__);exec(code,scope)
image=scope['strict_image'](before,after,{'func_151CEAAC':truth})
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_151CEAAC'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'functions':len(b),'all_addresses_fixed':True,'image':image,'protected_data':data,
 'owner_neighbors_unchanged':51,'caller_functions_unchanged':16,'caller_sections_changed':caller_sections,'uncredited':True}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
