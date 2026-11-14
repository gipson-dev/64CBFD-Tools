"""Check the typed direct caller with the actual owner compiler profile."""
from pathlib import Path
import inspect, json, shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-effect-dispatch-150b3ab0-durable';q.out=q.p.out=out
shutil.copyfile(root/'conker/retail_word_patches.us.csv',out/'proposed-guards.csv')
code=inspect.getsource(q.actual_make); needle="assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==1";assert code.count(needle)==1
scope=dict(q.actual_make.__globals__);exec(code.replace(needle,"assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==2"),scope)
targets,commands=scope['actual_make']({'game/generated_E0F60':out/'candidate-12.c','game_981E0':out/'caller-proposed.c'})
callerbase=root/'conker/build/src/game_981E0.c.o'; caller=targets['game_981E0']
count=same_functions(callerbase,caller);assert normalized_pools(callerbase)==normalized_pools(caller)
a,b=sections(callerbase),sections(caller);changed=sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k));assert set(changed)<={'.mdebug'},changed
elf=q.link(targets); before=(out/'frozen/conker/build/conker.us.elf').read_bytes(); after=elf.read_bytes()
truth=(root/'conker/conker.us.bin').read_bytes()[0xe0f60:0xe10bc]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
scope=dict(q.strict_image.__globals__);exec(code.replace(needle,"sizes={'func_150B3AB0':348}"),scope)
image=scope['strict_image'](before,after,{'func_150B3AB0':truth})
a,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_150B3AB0'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'caller_functions_unchanged':count,'caller_sections_changed':changed,'functions':len(a),'image':image,'protected_data':data,'uncredited':True}
(out/'caller-image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
